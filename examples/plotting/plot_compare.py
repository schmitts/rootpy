import ROOT

from rootpy.plotting import Hist
from rootpy.plotting.compare import hist_compare
from rootpy.interactive import wait
from rootpy.plotting.style import get_style

import random

h_data = Hist(100, -5, 5, title='data', drawstyle='pe', linewidth=2, markercolor="black", markerstyle = "largedot", legendstyle="LPE")
h_mc1 = Hist(100, -5, 5, title='mc1', drawstyle='hist', linecolor="black", linewidth=2, legendstyle="L")
h_mc2 = Hist(100, -5, 5, title='mc2', drawstyle='hist', linecolor="red", linewidth=2, legendstyle="L")

for i in xrange(10000):
    h_data.Fill(random.gauss(0, 2))
    h_mc1.Fill(random.gauss(0.5, 2))
    h_mc2.Fill(random.gauss(-0.25, 2))

with get_style('ATLAS'):

    hc = hist_compare(h_data, [h_mc1, h_mc2], ymin_compare=0.5, ymax_compare=1.5, xtitle_compare="x [m]", ytitle_compare="Data / MC", ytitle="#", )
    c = hc.prepare_canvas()
    hc.fill_pads(c.GetPad(1), c.GetPad(2), compare_legend=False)

    hc.allstack.GetHistogram().GetXaxis().SetLabelSize(0)
    hc.comparestack.GetHistogram().GetXaxis().SetTitleOffset(3)
    hc.comparestack.GetHistogram().GetYaxis().SetNdivisions(5,5,0)

    c.SaveAs("compare.png")

wait()
