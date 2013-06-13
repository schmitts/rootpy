import itertools

from .canvas import Canvas
from .hist import HistStack
from legend import Legend

class compare_helper(object):
    """

    Helper to compare a list of num to a list of denom. The actual
    compare class has to implement compare_func.

    num = [a, b]
    denom = [c, d]

    ->

    compare = [(a,c), (a,d), (b,c), (b,d)]

    """

    def __init__(self, num, denom):

        if not isinstance(num,list):
            self._num = [num]
        else:
            self._num = num

        if not isinstance(denom,list):
            self._denom = [denom]
        else:
            self._denom = denom

        self.compare_result = None

        self._compare()

    @property
    def num(self):
        return self._num

    @num.setter
    def num(self, n):
        self._num = n

    @property
    def denom(self):
        return self._denom

    @denom.setter
    def denom(self, d):
        self._denom = d

    def product(self):

        for n,d in itertools.product(self.num, self.denom):
            yield n,d

    @property
    def all(self):
        return self.num + self.denom

    def compare_func(self, n, d):
        """the function used for comparison has to take exactly two arguments"""

        raise NotImplementedError("")

    def _compare(self):

        self.compare_result = [self.compare_func(n,d) for n,d in self.product()]

class hist_compare(compare_helper):
    """

    Comparing histograms made easy.

    """

    cfg = {"xmin" : None, "xmax" : None,
           "ymin" : None, "ymax" : None,
           "ymin_compare" : None, "ymax_compare" : None,
           "xtitle" : None, "ytitle" : None,
           "xtitle_compare" : None, "ytitle_compare" : None}

    def __init__(self, *args, **kwargs):
        """

        xmin, xmax - range on x axis
        ...

        """

        # pop everything that should not reach hist_compare

        self.xmin = kwargs.pop('xmin', None)
        self.xmax = kwargs.pop('xmax', None)

        self.ymin = kwargs.pop('ymin', None)
        self.ymax = kwargs.pop('ymax', None)

        self.ymin_compare = kwargs.pop('ymin_compare', None)
        self.ymax_compare = kwargs.pop('ymax_compare', None)

        self.xtitle = kwargs.pop('xtitle', None)
        self.ytitle = kwargs.pop('ytitle', None)

        self.xtitle_compare = kwargs.pop('xtitle_compare', None)
        self.ytitle_compare = kwargs.pop('ytitle_compare', None)

        # pass remaining args and kwargs
        super(hist_compare, self).__init__(*args, **kwargs)

        # keep clones of nums and denoms
        self.num = [h.Clone() for h in self.num]
        self.denom = [h.Clone() for h in self.denom]

    def compare_func(self, n, d):

        c = n.Clone()
        c.title = "%s / %s" % (n.title, d.title)

        c.Divide(d)

        c.linecolor = d.linecolor
        c.markerstyle = d.markerstyle
        c.markercolor = d.linecolor
        c.drawstyle = n.drawstyle
        c.legendstyle = "PLE"

        return c

    @property
    def yaxis(self):
        return self.allstack.GetHistogram().GetYaxis()

    @property
    def xaxis(self):
        return self.allstack.GetHistogram().GetXaxis()

    @property
    def yaxis_compare(self):
        return self.comparestack.GetHistogram().GetYaxis()

    @property
    def xaxis_compare(self):
        return self.comparestack.GetHistogram().GetXaxis()

    def _legend_helper(self, toleg, *args, **kwargs):

        leg = Legend(len(toleg), *args, **kwargs)
        for h in toleg:
            leg.AddEntry(h)
        return leg

    def prepare_canvas(self, frac=0.3, margin=0.05, width=800, height=800):

        c = Canvas(width,height)
        c.Divide(1,2)

        all_pad = c.GetPad(1)
        compare_pad = c.GetPad(2)

        c.all_pad = all_pad
        c.compare_pad = compare_pad

        all_pad.SetPad(0,frac,1,1)
        compare_pad.SetPad(0,0,1,frac)

        main_frac = 1-frac;
        left_bottom_margin = 2.1*margin;

        # no gap between main and ratio pad
        all_pad.SetBottomMargin(0.02)
        compare_pad.SetTopMargin(0)

        all_pad.SetRightMargin(margin)
        compare_pad.SetRightMargin(margin)

        all_pad.SetLeftMargin(left_bottom_margin)
        compare_pad.SetLeftMargin(left_bottom_margin)

        all_pad.SetTopMargin(margin/main_frac)
        compare_pad.SetBottomMargin(left_bottom_margin/frac)

        compare_pad.SetGrid(0,2)

        return c

    def fill_pads(self, all_pad, compare_pad, all_legend=True, compare_legend=True):

        self.allstack = HistStack(hists=reversed(self.all), drawstyle="nostack")
        self.comparestack = HistStack(hists=self.compare_result, drawstyle="nostack")

        self.alllegend = self._legend_helper(self.all)
        self.comparelegend = self._legend_helper(self.compare_result)

        all_pad.cd()
        self.allstack.Draw()
        if all_legend:
            self.alllegend.Draw()

        compare_pad.cd()
        self.comparestack.Draw()
        if compare_legend:
            self.comparelegend.Draw()

        all_pad.Modified()
        all_pad.Update()
        compare_pad.Modified()
        compare_pad.Update()

        if self.xtitle != None:
            self.xaxis.SetTitle(self.xtitle)
        else:
            self.xaxis.SetTitle(self.all[0].GetXaxis().GetTitle())

        if self.ytitle != None:
            self.yaxis.SetTitle(self.ytitle)
        else:
            self.yaxis.SetTitle(self.all[0].GetYaxis().GetTitle())

        if self.xtitle_compare != None:
             self.xaxis_compare.SetTitle(self.xtitle_compare)
        else:
             self.xaxis_compare.SetTitle(self.all[0].GetXaxis().GetTitle())

        if self.ytitle_compare:
            self.yaxis_compare.SetTitle(self.ytitle_compare)
        else:
            self.yaxis_compare.SetTitle(self.all[0].GetYaxis().GetTitle())

        if self.xmin != None or self.xmax != None:

            self.xaxis.SetRangeUser(self.xmin if self.xmin else self.xaxis.GetXmin(),
                                    self.xmax if self.xmax else self.xaxis.GetXmax()
                                    )

            self.xaxis_compare.SetRangeUser(self.xmin if self.xmin else self.xaxis_compare.GetXmin(),
                                            self.xmax if self.xmax else self.xaxis_compare.GetXmax()
                                            )

        if self.ymin_compare != None:
            self.comparestack.SetMinimum(self.ymin_compare)

        if self.ymax_compare != None:
            self.comparestack.SetMaximum(self.ymax_compare)

        if self.ymin != None:
            self.allstack.SetMinimum(self.ymin)

        if self.ymax != None:
            self.allstack.SetMaximum(self.ymax)

        all_pad.Modified()
        all_pad.Update()
        compare_pad.Modified()
        compare_pad.Update()
