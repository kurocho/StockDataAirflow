from airflow.decorators import dag, task, task_group
from datetime import datetime
from airflow.operators.python import PythonOperator, PythonVirtualenvOperator
from airflow.exceptions import AirflowSkipException

default_args = {'start_date': datetime(2022, 1, 1)}
BATCH_SIZE = 10
@dag(
    'stock_data_dag',
    schedule_interval='0 0 * * 1-5',
    default_args=default_args,
    catchup=False,
    tags=['stock'],
)
def taskflow():


    @task
    def init():
        from os import path, mkdir
        if not path.exists("tmp"):
            mkdir("tmp")
        if not path.exists("reports"):
            mkdir("reports")

    @task
    def get_tickers():
        import requests
        import re
        from bs4 import BeautifulSoup

        html_tags_regex = r'<[^<]+?>'

        def parse_tickers(ticker_divs):
            return [re.sub(html_tags_regex, '', str(x)) for x in ticker_divs]

        URL = "https://www.earningswhispers.com/calendar?sb=p&d=1&t=all"
        page = requests.get(URL)

        soup = BeautifulSoup(page.content, "html.parser")
        ticker_elements = soup.find_all("div", class_="ticker")

        return {'tickers': parse_tickers(ticker_elements)}
    
    

    @task
    def get_stock_data(tickers: list, index):
        import yfinance as yf
        import pickle
        import datetime
        def get_financial_data(ticker):
                stock = yf.Ticker(ticker)
                #info 
                info = stock.info
                # get historical market data
                hist = stock.history(period="3mo", interval="1d")
                quarterly_financials = stock.quarterly_financials
                # show major holders
                major_holders = stock.major_holders
                # show news
                # TODO error news = stock.news
                # get option chain for specific expiration
                return info, hist, quarterly_financials, major_holders
        

        skipped = True
        for i in range(0,len(tickers['tickers'])):
            if i % BATCH_SIZE == index:
                ticker = tickers['tickers'][i]
                print("Getting stock data for: " + ticker)
                data = get_financial_data(ticker)

                today = datetime.datetime.today()
                tomorrow = today + datetime.timedelta(days=1)
                tomorrow_date = str(tomorrow).split(" ")[0]
                filename = f'tmp/{ticker}_{tomorrow_date}.pickle'
                with open(filename, 'wb') as handle:
                    print("Saving pickle for: " + ticker)
                    pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)

                skipped = False

        if skipped:
            raise AirflowSkipException

        return tickers['tickers']

    @task(trigger_rule="all_done")
    def generate_report(tickers_dict: list):
        print("Report generation start")
        tickers = tickers_dict[0]
        from fpdf import FPDF
        import datetime
        import matplotlib.pyplot as plt
        import pickle

        today = datetime.datetime.today()
        tomorrow = today + datetime.timedelta(days=1)
        tomorrow_date = str(tomorrow).split(" ")[0]

        pdf = FPDF()
    
        # Add a page
        pdf.add_page()
        
        # set style and size of font 
        # that you want in the pdf
        pdf.set_font("Arial", size = 15)
        # create a cell
        pdf.cell(200, 10, txt = "Stock Earnings Report", 
                ln = 1, align = 'C')

        pdf.cell(200, 10, txt = tomorrow_date, 
                ln = 1, align = 'C')
        decoded_tickers = dict()
        for ticker in tickers:
            filename = f'tmp/{ticker}_{tomorrow_date}.pickle'
            print(f'For {ticker}:')
            with open(filename, 'rb') as handle:
                decoded_tickers[ticker] = pickle.load(handle)

                pdf.set_font("Arial", size = 15)
                pdf.cell(150, 8, txt = ticker,
                        ln = 1, align = 'A')
                pdf.set_font("Arial", size = 10)
                sector = decoded_tickers[ticker][0]['sector']
                employees = decoded_tickers[ticker][0]['fullTimeEmployees']
                summary = decoded_tickers[ticker][0]['longBusinessSummary']
                website = decoded_tickers[ticker][0]['website']
                pdf.cell(150, 4, txt = f'Sector: {sector}',
                        ln = 0, align = 'A')
                pdf.cell(150, 4, txt = f'Employees: {employees}',
                        ln = 1, align = 'B')
                pdf.set_font("Arial", size = 8)
                pdf.cell(150, 4, txt = f'Website: {website}',link=website,
                        ln = 1, align = 'A')
                pdf.multi_cell(180, 3, txt = summary, align = 'A')
                history = decoded_tickers[ticker][1]
                # Volume fig
                pdf.set_font("Arial", size = 10)
                pdf.cell(150, 4, txt = f'Volume', ln = 1, align = 'A')
                fig = plt.figure()
                fig = history['Volume'].plot().get_figure()
                fig.savefig(f'tmp/volume_{ticker}.png',dpi=300)
                pdf.image(f'tmp/volume_{ticker}.png',w=100)
                
                # Price
                pdf.set_font("Arial", size = 10)
                pdf.cell(150, 4, txt = f'Price', ln = 1, align = 'A')
                fig = plt.figure()
                fig = history.loc[:,['Open','Close']].plot().get_figure()
                fig.savefig(f'tmp/price_{ticker}.png',dpi=300)
                pdf.image(f'tmp/price_{ticker}.png',w=100)

                pdf.add_page()
        pdf.output(f'reports/Report_{tomorrow_date}.pdf') 
 
    
    @task
    def end(value):
        print(f'this is the end: {value}')



    # THIS IS DAG TASK ORDERING
    init_task = init()
    tickers_task = get_tickers()
    stock_data_tasks = []
    for i in range(0,BATCH_SIZE):
        stock_data_tasks.append(get_stock_data(tickers_task,i))

    return end(generate_report(stock_data_tasks))


dag = taskflow()
