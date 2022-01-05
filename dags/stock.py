from airflow.decorators import dag, task
from datetime import datetime


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

        def get_financial_data(ticker):
            import yfinance as yf

            msft = yf.Ticker(ticker)

            # get stock info
            msft.info

            # get historical market data
            hist = msft.history(period="max")

            # show actions (dividends, splits)
            msft.actions

            # show dividends
            msft.dividends

            # show splits
            msft.splits

            # show financials
            msft.financials
            msft.quarterly_financials

            # show major holders
            msft.major_holders

            # show institutional holders
            msft.institutional_holders

            # show balance sheet
            msft.balance_sheet
            msft.quarterly_balance_sheet

            # show cashflow
            msft.cashflow
            msft.quarterly_cashflow

            # show earnings
            msft.earnings
            msft.quarterly_earnings

            # show sustainability
            msft.sustainability

            # show analysts recommendations
            msft.recommendations

            # show next event (earnings, etc)
            msft.calendar

            # show ISIN code - *experimental*
            # ISIN = International Securities Identification Number
            msft.isin

            # show options expirations
            msft.options

            # show news
            msft.news

            # get option chain for specific expiration
            return msft.option_chain('2022-01-21')
        for ticker in tickers['tickers']:
            get_financial_data(ticker)


    
    

    tickers_task = get_tickers(state)
    stock_data_task = get_stock_data(tickers_task)

dag = taskflow()