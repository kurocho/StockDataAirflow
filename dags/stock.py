from airflow.decorators import dag, task
from datetime import datetime
from airflow.operators.python import PythonOperator, PythonVirtualenvOperator

state = 'wa'

default_args = {
    'start_date': datetime(2022, 1, 1)
}

@dag('stock_data_dag', schedule_interval='@daily', default_args=default_args, catchup=False, tags=['stock'])
def taskflow():

    @task.virtualenv(
        use_dill=True,
        system_site_packages=False,
        requirements=['beautifulsoup4','requests'],
    )
    def get_tickers(state):
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
        return{'tickers': parse_tickers(ticker_elements)}

    @task.virtualenv(
        use_dill=True,
        system_site_packages=False,
        requirements=['yfinance'],
    )
    def get_stock_data(tickers: list):
        print(tickers)

        import yfinance as yf

        def get_financial_data(ticker):
            stock = yf.Ticker(ticker)
            return stock

        for ticker in tickers['tickers']:
            get_financial_data(ticker)

    tickers_task = get_tickers(state)
    stock_data_task = get_stock_data(tickers_task)

dag = taskflow()