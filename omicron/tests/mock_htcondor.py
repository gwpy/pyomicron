#!/usr/bin/env python

"""This module is a mock of htcondor.py, purely for testing
"""


class Schedd(object):
    """Mock of the `htcondor.Schedd` object
    """
    _jobs = []

    def query(self, constraints, attr_list=[], **kwargs):
        print('_jobs', self._jobs)
        x = {}
        for con in constraints.split(' && '):
            try:
                a, b = con.split(' == ')
            except ValueError:
                break
            else:
                x[a] = eval(b)
        match = []

        def match(job):
            for key in x:
                if x[key] != job[key]:
                    return False
            return True

        return iter(filter(match, self._jobs))

    def history(self, *args, **kwargs):
        return
