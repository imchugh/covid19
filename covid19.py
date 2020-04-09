#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 21:35:22 2020

@author: imchugh
"""

from datetime import datetime as dt
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import urllib.request
import pdb

#------------------------------------------------------------------------------
class national_updates():

    def __init__(self):

        self.feed_url = 'https://interactive.guim.co.uk/docsdata/1q5gdePANXci8enuiS4oHUJxcxC13d6bjMRSicakychE.json'
        self.states = ['ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA']

    def get_raw_data(self):

        with urllib.request.urlopen(self.feed_url) as url:
            data = json.loads(url.read().decode())
        return data

    def get_formatted_data(self, state=None):

        if state:
            try: assert state in self.states
            except AssertionError: print('Not a state or Territory of '
                                         'Australia!')
        data = self.get_raw_data()
        l = []
        for x in data['sheets']['updates']: l.append(list(x.values()))
        cols = list(x.keys())
        df = pd.DataFrame(l, columns=cols)
        new_cols = cols[1:3] + cols[:1] + cols[3:]
        df = df[new_cols]
        df['Date'] = pd.Series(
            [dt.strftime(dt.strptime(x, '%d/%m/%Y'), '%Y-%m-%d')
             for x in df.Date])
        df.index = pd.to_datetime(df.Date + ' ' + df.Time.str.replace('.', ':'),
                                  errors='coerce')
        df.sort_index(inplace=True)
        df.index = pd.to_datetime(df.Date)
        return (
                pd.concat([df[new_cols[:3]],
                           df[new_cols[3:10]].apply(_clean_numeric_data)],
                          axis=1)
                .drop(['Date', 'Time'], axis=1)
                .pipe(_reindex_states, self.states)
                )

    def plot_confirmed_cases_by_state(self, states=[], daily=False):

        """Plot number of cases by state:
            kwargs:
                * states(list of strings): states to plot (default all);
                * daily (bool, default False): plots cumulative counts when
                  False, daily counts when true"""

        df = self.get_formatted_data()
        state_list = df.State.unique()
        if not len(states)==0:
            try:
                for x in states: assert x in state_list
            except AssertionError:
                print('{} is not a state or territory'.format(x))
        else:
            states = state_list
        idx = df.index.unique()
        bottom_series = pd.Series(np.zeros(len(idx)), index=idx)
        fig, ax = plt.subplots(1, 1, figsize = (12, 8))
        xlab = 'Cumulative confirmed cases'
        if daily: xlab = 'Daily confirmed cases'
        _basic_plot_setup(ax, 'Date', xlab)
        for this_state in states:
            s = (df['Cumulative case count'].loc[df.State==this_state]
                 .interpolate()
                 .fillna(0))
            if daily: s = (s-s.shift()).fillna(0)
            ax.bar(s.index, s, label=this_state, bottom=bottom_series)
            bottom_series += s
        ax.legend(frameon=False, loc='upper left')
        return

    def plot_proportion_tests_positive(self, states=[]):

        """Plot number of cases by state:
            kwargs:
                * states(list of strings): states to plot (default all);
                * daily (bool, default False): plots cumulative counts when
                  False, daily counts when true"""

        df = self.get_formatted_data()
        state_list = df.State.unique()
        if not len(states)==0:
            try:
                for x in states: assert x in state_list
            except AssertionError:
                print('{} is not a state or territory'.format(x))
        else:
            states = state_list
        idx = df.index.unique()
        bottom_series = pd.Series(np.zeros(len(idx)), index=idx)
        fig, ax = plt.subplots(1, 1, figsize = (12, 8))
        xlab = 'Tests +ve per 100,000'
        _basic_plot_setup(ax, 'Date', xlab)
        for this_state in states:
            s = ((df['Tests conducted (total)'].loc[df.State==this_state] -
                  df['Tests conducted (negative)'].loc[df.State==this_state]) /
                 df['Tests conducted (total)'].loc[df.State==this_state] *
                 10**5)
            ax.bar(s.index, s, label=this_state, bottom=bottom_series)
            bottom_series += s
        ax.legend(frameon=False, loc='upper left')
        return
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
class international_updates():

    def __init__(self):

        self.csv_url = ('https://opendata.ecdc.europa.eu/covid19/'
                         'casedistribution/csv')
        self.data = self.get_formatted_data()

    def get_country_territory_list(self):

        return self.data.countriesAndTerritories.unique().tolist()

    def get_formatted_data(self):

       usecols =['dateRep', 'cases', 'deaths', 'countriesAndTerritories',
                 'geoId', 'countryterritoryCode', 'popData2018']
       df = pd.read_csv(self.csv_url, date_parser=_date_parser,
                        parse_dates=['dateRep'], index_col=['dateRep'],
                        usecols=usecols)
       new_index = pd.date_range(df.index.min(), df.index.max(), freq='D')
       return pd.concat([df.loc[df.countriesAndTerritories==this_country]
                                .reindex(new_index)
                                .interpolate()
                                .pipe(_fill_text)
                         for this_country in df.countriesAndTerritories.unique()])

    def get_case_fatality_rate_by_country(self, countries):

        df = self.data
        _check_country_list(df, countries)
        return {country: int(
                df.loc[df.countriesAndTerritories==country, 'deaths'].sum() /
                df.loc[df.countriesAndTerritories==country, 'cases'].sum()
                * 10**5
                ) for country in countries}

    def get_infection_rate_by_country(self, countries):

        df = self.data
        _check_country_list(df, countries)
        return {country: int(
                df.loc[df.countriesAndTerritories==country, 'cases'].sum() /
                df.loc[df.countriesAndTerritories==country, 'popData2018'].max()
                * 10**5
                ) for country in countries}

    def plot_confirmed_cases_by_country(self, countries, log_scale=True, daily=False):

        df = self.data
        country_list = df.countriesAndTerritories.unique().tolist()
        try:
            for x in countries: assert x in country_list
        except AssertionError:
            print('{} is not a country or territory'.format(x))
        fig, ax = plt.subplots(1, 1, figsize = (12, 8))
        ax.set_yscale('log')
        _basic_plot_setup(ax, 'Date', 'Case count')
        for country in countries:
            series = df.loc[df.countriesAndTerritories==country, 'cases']
            if not daily: ax.plot(series.cumsum(), label=country)
            if daily: ax.plot(series, label=country)
        ax.legend(frameon=False)
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
### FUNCTIONS ###
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def _basic_plot_setup(this_ax, x_label, y_label):

        this_ax.xaxis.set_ticks_position('bottom')
        this_ax.yaxis.set_ticks_position('left')
        this_ax.spines['right'].set_visible(False)
        this_ax.spines['top'].set_visible(False)
        this_ax.tick_params(axis = 'x', labelsize = 12)
        this_ax.tick_params(axis = 'y', labelsize = 12)
        this_ax.set_xlabel(x_label, fontsize = 14)
        this_ax.set_ylabel(y_label, fontsize = 14)

def _clean_numeric_data(series):

    return (
        pd.to_numeric(series.str.replace(',', '').replace('-', ''))
        .interpolate()
        .fillna(0)
        )

def _check_country_list(df, countries):

    country_list = df.countriesAndTerritories.unique().tolist()
    try:
        for x in countries: assert x in country_list
    except AssertionError:
        raise RuntimeError('{} is not a country or territory'.format(x))

def _date_parser(this_date):

    return dt.strptime(this_date, '%d/%m/%Y')

def _fill_text(df):

    for col in ['countriesAndTerritories', 'countryterritoryCode', 'geoId']:
        df[col].fillna(df[col].dropna().unique().item(), inplace=True)
        return df

def _reindex_states(df, state_list):

    new_index = pd.date_range(df.index[0], df.index[-1], freq='D')
    df_list = []
    for state in state_list:
        sub_df = df.loc[df.State==state]
        sub_df = sub_df[~sub_df.index.duplicated(keep='last')]
        sub_df = sub_df.reindex(new_index)
        sub_df['State'] = state
        df_list.append(sub_df)
    return pd.concat(df_list)

