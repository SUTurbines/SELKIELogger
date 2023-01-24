import wx

from .SLCChooseType import SLCChooseType
from .SLCGeneric import SLCGeneric
from .SLCMPConfig import SLCMPConfig
from .SLCSerialConfig import SLCSerialConfig

from SELKIELogger.Config import SLCAuto

sourceWindows = {
    "GPS": SLCGeneric,
    "SL": SLCMPConfig,
    "SERIAL": SLCSerialConfig,
}


def addSource(parent):
    with SLCChooseType(parent, title="Log settings") as dlg:
        if dlg.ShowModal():
            # Create some config instance class
            if len(dlg.ctType.GetValue()) == 0:
                print("Blank type")
                return
            key = dlg.ctType.GetValue().split(":")[0]
        else:
            return

    nextWindow = SLCGeneric
    if key in sourceWindows:
        nextWindow = sourceWindows[key]

    with nextWindow(parent, title="Create source") as dlg:
        if isinstance(dlg, SLCGeneric):
            dlg.type.SetValue(key)

        if dlg.ShowModal() == wx.ID_OK:
            try:
                obj = dlg.generateSource()
                parent.config.addSource(obj)
            except Exception as e:
                m = wx.MessageDialog(
                    dlg,
                    caption="Failed to add source",
                    message="Unable to add source using the information provided",
                    style=wx.ICON_WARNING,
                )
                m.SetExtendedMessage(f"Additional details:\n{e}")
                m.ShowModal()

    updateGrid(parent)


def editSource(parent):
    blocks = parent.sourcelist.GetSelectedRowBlocks()
    if len(blocks) == 0:
        return
    rows = []
    for b in blocks:
        rows.extend(range(b.TopRow, b.BottomRow + 1))

    if len(rows) != 1:
        wx.MessageDialog(
            parent,
            caption="Edit soruces",
            message="Sources can only be edited individually",
            style=wx.OK | wx.ICON_ERROR | wx.CENTRE,
        ).ShowModal()
        return

    editWindow = SLCGeneric
    tag = parent.sourcelist.GetCellValue(row=rows[0], col=0)
    sourceType = parent.sourcelist.GetCellValue(row=rows[0], col=1)
    if sourceType in sourceWindows:
        editWindow = sourceWindows[sourceType]

    with editWindow(parent, title=f"Edit source: {tag}") as dlg:
        dlg.updateFromSource(parent.sources[tag])
        if dlg.ShowModal() == wx.ID_OK:
            try:
                obj = dlg.generateSource()
                parent.config.updateSource(obj)
            except Exception as e:
                m = wx.MessageDialog(
                    dlg,
                    caption="Failed to update source",
                    message="Unable to update source using the information provided",
                    style=wx.ICON_WARNING,
                )
                m.SetExtendedMessage(f"Additional details:\n{e}")
                m.ShowModal()

    updateGrid(parent)


def deleteSource(parent):
    blocks = parent.sourcelist.GetSelectedRowBlocks()
    if len(blocks) == 0:
        return
    rows = []
    for b in blocks:
        rows.extend(range(b.TopRow, b.BottomRow + 1))
    tags = []
    for r in rows:
        tags.extend([parent.sourcelist.GetCellValue(row=r, col=0)])

    m = wx.MessageDialog(
        parent,
        caption="Remove sources",
        message=f"Are you sure you want to remove sources with the following tags?",
        style=wx.YES_NO,
    )
    m.SetExtendedMessage(", ".join(tags))
    if m.ShowModal() == wx.ID_YES:
        for t in tags:
            parent.config.removeSource(t)

    updateGrid(parent)


def updateGrid(main):
    main.sourcelist.ClearGrid()
    main.sourcelist.BeginBatch()
    try:
        rn = 0
        for i in main.config.sources:
            if rn >= main.sourcelist.GetNumberRows():
                main.sourcelist.AppendRows(1)
            main.sourcelist.SetCellValue(
                row=rn, col=0, s=str(main.config.sources[i].tag)
            )
            main.sourcelist.SetCellValue(
                row=rn, col=1, s=str(main.config.sources[i].sourceType)
            )
            main.sourcelist.SetCellValue(row=rn, col=2, s=str(main.config.sources[i]))
            rn += 1
        if rn < main.sourcelist.GetNumberRows():
            main.sourcelist.DeleteRows(rn, main.sourcelist.GetNumberRows() - rn)
    finally:
        main.sourcelist.EndBatch()
