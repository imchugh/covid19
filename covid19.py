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

class updates():

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
                           df[new_cols[3:10]].apply(pd.to_numeric)],
                          axis=1)
                .drop(['Date', 'Time'], axis=1)
                .pipe(_reindex_states, self.states)
                )

    def plot_confirmed_cases_by_state(self, states=[], daily=False):

        """Plot number of cases by state:
            * kwargs:
                states(list of strings): states to plot (default all);
                daily (bool, default False): plots cumulative counts when
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

def _basic_plot_setup(this_ax, x_label, y_label):

        this_ax.xaxis.set_ticks_position('bottom')
        this_ax.yaxis.set_ticks_position('left')
        this_ax.spines['right'].set_visible(False)
        this_ax.spines['top'].set_visible(False)
        this_ax.tick_params(axis = 'x', labelsize = 12)
        this_ax.tick_params(axis = 'y', labelsize = 12)
        this_ax.set_xlabel(x_label, fontsize = 14)
        this_ax.set_ylabel(y_label, fontsize = 14)

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

