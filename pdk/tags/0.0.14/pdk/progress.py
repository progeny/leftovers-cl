#   Copyright 2005 Progeny Linux Systems, Inc.
#
#   This file is part of PDK.
#
#   PDK is free software; you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   PDK is distributed in the hope that it will be useful, but WITHOUT
#   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#   or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
#   License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with PDK; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

'''progress.py

Display a progress meter on the console.

'''

import sys

class CurlAdapter(object):
    '''Adapt the ConsoleProgress class to handle the curl progress
    callback
    '''

    def __init__(self, progress):
        self.progress = progress

        self.started = False
        self.done = False

    def callback(self, down_total, down_now, up_total, up_now):
        '''Call progress methods as appropriate.

        total - total amount of work to be done. 0 for unbounded.
        current - current amount of work accomplished.

        When unbounded, non-zero implies still working, zero implies
        done.
        '''
        if self.done:
            return

        total = down_total + up_total
        now = down_now + up_now

        if not self.started:
            self.progress.start()
            self.started = True

        if total == 0:
            self.progress.write_spin()
            self.progress.done()
            self.done = True
        else:
            self.progress.write_bar(total, now)

        if total == now:
            self.progress.done()
            self.done = True

class ConsoleProgress(object):
    '''Display a progress meter on the console.

    Call start before write_bar or write_spin.
    Use write_bar for bounded.
    Use write_spin for unbounded work.
    Call done when finished.
    '''
    def __init__(self, name, output_file = sys.stderr):
        self.name = name
        self.output_file = output_file
        self.bar_len = 60

        self.spinner = { '-': '+', '+': '-' }
        self.spinner_current = '-'

    def start(self):
        '''Write the name of this bar to the handle if neccessary.'''
        if self.name:
            self.output_file.write(self.name + '\n')
            self.output_file.flush()

    def done(self):
        '''Insert a real line break.'''
        self.output_file.write('\n')
        self.output_file.flush()

    def write_bar(self, total, current):
        '''Write the current progress to the handle.

        total - total amount of work to be done. 0 for unbounded.
        current - current amount of work accomplished.

        When unbounded, non-zero implies still working, zero implies
        done.
        '''
        ticks = int(self.bar_len * float(current) / float(total))
        if ticks < 0:
            ticks = 0
        if ticks > self.bar_len:
            ticks = self.bar_len
        spaces = self.bar_len - ticks
        bar_string = '|' + ticks * '=' + spaces * ' ' + '|\r'

        self.output_file.write(bar_string)
        self.output_file.flush()

    def write_spin(self):
        '''Write a spinner to the handle.'''
        bar_string = '|' + self.bar_len * self.spinner_current + '|\r'
        self.spinner_current = self.spinner[self.spinner_current]

        self.output_file.write(bar_string)
        self.output_file.flush()
