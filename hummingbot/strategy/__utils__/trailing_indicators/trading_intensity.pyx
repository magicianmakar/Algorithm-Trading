from math import floor, ceil
from decimal import Decimal
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.optimize import OptimizeWarning
import csv
import warnings

from typing import (
    Tuple,
)


cdef class TradingIntensityIndicator():

    def __init__(self, sampling_length: int = 30, order_amount: float = 1, price_levels: Tuple[float] = (0)):
        self._alpha = 0
        self._kappa = 0
        self._trades = []
        self._bids_df = None
        self._asks_df = None
        self._order_amount = order_amount
        self._sampling_length = sampling_length
        self._samples_length = 0

        warnings.simplefilter("ignore", OptimizeWarning)

    def _simulate_execution(self, timestamp, bids_df, asks_df):
        # Estimate market orders that happened
        # Assume every movement in the BBO is caused by a market order and its size is the volume differential

        bid = bids_df["price"].iloc[0]
        ask = asks_df["price"].iloc[0]
        price = (bid + ask) / 2

        bid_prev = self._bids_df["price"].iloc[0]
        ask_prev = self._asks_df["price"].iloc[0]
        price_prev = (bid_prev + ask_prev) / 2

        trades = []

        # Higher bids were filled - someone matched them - a determined seller
        # Equal bids - if amount lower - partially filled
        for index, row in self._bids_df[self._bids_df['price'] >= bid].iterrows():
            if row['price'] == bid:
                if bids_df["amount"].iloc[0] < row['amount']:
                    amount = row['amount'] - bids_df["amount"].iloc[0]
                    price_level = abs(row['price'] - price_prev)
                    trades += [{'price_level': price_level, 'amount': amount}]
            else:
                amount = row['amount']
                price_level = abs(row['price'] - price_prev)
                trades += [{'price_level': price_level, 'amount': amount}]

        # Lower asks were filled - someone matched them - a determined buyer
        # Equal asks - if amount lower - partially filled
        for index, row in self._asks_df[self._asks_df['price'] <= ask].iterrows():
            if row['price'] == ask:
                if asks_df["amount"].iloc[0] < row['amount']:
                    amount = row['amount'] - asks_df["amount"].iloc[0]
                    price_level = abs(row['price'] - price_prev)
                    trades += [{'price_level': price_level, 'amount': amount}]
            else:
                amount = row['amount']
                price_level = abs(row['price'] - price_prev)
                trades += [{'price_level': price_level, 'amount': amount}]

        # Add trades
        self._trades += [trades]
        if len(self._trades) > self._sampling_length:
            self._trades = self._trades[1:]

    def _estimate_intensity(self):
        # Calculate lambdas / trading intensities
        lambdas = []

        trades_consolidated = {}
        price_levels = []
        for tick in self._trades:
            for trade in tick:
                if trade['price_level'] not in trades_consolidated.keys():
                    trades_consolidated[trade['price_level']] = 0
                    price_levels += [trade['price_level']]

                trades_consolidated[trade['price_level']] += trade['amount']

        price_levels = sorted(price_levels, reverse=True)

        with open('/Users/matejhorvath/github/hummingbot/logs/intensity.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            for price_level in price_levels:
                if len(lambdas) == 0:
                    lambdas += [trades_consolidated[price_level]]
                else:
                    lambdas += [trades_consolidated[price_level]]
                writer.writerow([price_level, lambdas[-1]])

        # Adjust to be able to calculate log
        lambdas_adj = [10**-10 if x==0 else x for x in lambdas]

        # Fit the probability density function; reuse previously calculated parameters as initial values
        try:
            params = curve_fit(lambda t, a, b: a*np.exp(-b*t), price_levels, lambdas_adj, p0=(self._alpha, self._kappa), method='dogbox')

            self._kappa = Decimal(str(params[0][1]))
            self._alpha = Decimal(str(params[0][0]))
        except (RuntimeError, ValueError) as e:
            pass

    def add_sample(self, timestamp: float, value: Tuple[pd.DataFrame, pd.DataFrame]):
        bids_df = value[0]
        asks_df = value[1]

        if bids_df.empty or asks_df.empty:
            return

        # Skip snapshots where no trades occured
        if self._bids_df is not None and self._bids_df.equals(bids_df):
            return

        if self._asks_df is not None and self._asks_df.equals(asks_df):
            return

        if self._bids_df is not None and self._asks_df is not None:
            # Retrieve previous order book, evaluate execution
            self._simulate_execution(timestamp, bids_df, asks_df)

            # Estimate alpha and kappa
            self._estimate_intensity()

        # Store the orderbook
        self._bids_df = bids_df
        self._asks_df = asks_df

    @property
    def current_value(self) -> Tuple[float, float]:
        return self._alpha, self._kappa

    @property
    def is_sampling_buffer_full(self) -> bool:
        return len(self._trades) == self._sampling_length

    @property
    def is_sampling_buffer_changed(self) -> bool:
        is_changed = self._samples_length != len(self._trades)
        self._samples_length = len(self._trades)
        return is_changed
