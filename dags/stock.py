from airflow.decorators import dag, task
from datetime import datetime
from airflow.operators.python import PythonOperator, PythonVirtualenvOperator
from airflow.exceptions import AirflowException

default_args = {'start_date': datetime(2022, 1, 1)}
BATCH_SIZE = 10

@dag(
    'stock_data_dag',
    schedule_interval='@daily',
    default_args=default_args,
    catchup=False,
    tags=['stock'],
)
def taskflow():
    @task.virtualenv(
        use_dill=True,
        system_site_packages=False,
        requirements=['beautifulsoup4', 'requests'],
    )

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
    
    

    @task.virtualenv(
        use_dill=True,
        system_site_packages=True,
        requirements=['yfinance']
    )
    def get_stock_data(tickers: list, index, BATCH_SIZE):
        import yfinance as yf
        def get_financial_data(ticker):
            stock = yf.Ticker(ticker)
            return stock

        skipped = True
        for i in range(0,len(tickers['tickers'])):
            if i % BATCH_SIZE == index:
                ticker = tickers['tickers'][i]
                print("Getting stock data for: " + ticker)
                get_financial_data(ticker)
                skipped = False

        if skipped:
            print("SKIPPED")
        

    tickers_task = get_tickers()
    for i in range(0,BATCH_SIZE):
        stock_data_task = get_stock_data(tickers_task,i,BATCH_SIZE)


dag = taskflow()
