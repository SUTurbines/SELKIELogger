#!/usr/bin/env python3

import wx
import gettext
from SLConfig.SLConfigGUIMain import SLConfigGUIMain
from SELKIELogger.scripts import log
from SELKIELogger.Config import SLConfiguration


class SLConfigGUI(wx.App):
    def OnInit(self):
        self._mw = SLConfigGUIMain(None, wx.ID_ANY, "")
        self.SetTopWindow(self._mw)
        self._mw.config = SLConfiguration()
        self._mw.Show()
        return True


if __name__ == "__main__":
    log.info("Begin program")
    gettext.install("SLConfig")  # replace with the appropriate catalog name

    SLConfig = SLConfigGUI(0)
    log.info("Begin mainloop")
    SLConfig.MainLoop()
