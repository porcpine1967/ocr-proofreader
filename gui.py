#!/usr/bin/env python

import array
import Image

import wx
import wx.lib.rcsizer as rcs

import line_manager
import spell_checker

class App(wx.App):
    def OnInit(self):
        self.line_manager = None
        self.frame = BaseFrame(parent=None, title="Test App", size=(600, 600))
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True

    def set_line_manager(self, line_manager):
        self.frame.set_line_manager(line_manager)

class BaseFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.page_nbr = 0
        self.line = None
	# Make Panel
	self.panel = wx.Panel(self, -1)
        self.current_text = rcs.RowColSizer()
	self.pageCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, str(self.page_nbr), 
            size=(40, 20,), style=wx.TE_READONLY)
	self.sizeCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(500,80,), style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.current_text.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Page'), row=1, col=1)
	self.editCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(500, 20,), style=wx.TE_PROCESS_ENTER)
        blank_page_manager = PageBitmapManager('', 500)
        self.imageCtrl = wx.StaticBitmap(self.panel, wx.ID_ANY, 
            blank_page_manager.get_bitmap(80, 80), size=(500, 80,)) 


        self.Bind(wx.EVT_TEXT_ENTER, self.OnEdit, self.editCtrl)
        self.current_text.Add(self.pageCtrl, row=1, col=2)
        self.current_text.Add(self.sizeCtrl, row=2, col=2)
        self.current_text.Add(self.editCtrl, row=3, col=2)
        self.current_text.Add(self.imageCtrl, row=4, col=2)

    def OnEdit(self, event):
        self.line.text = event.GetString()
        self.line.rebuild()
        event.Skip()
    def OnNextBadLine(self, event):
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line = self.lm.next_line_to_check(self.page_nbr, self.line)
        self.pageCtrl.SetValue(str(self.page_nbr))
        if self.line:
            if old_page_nbr != self.page_nbr:
                self.bitmap_fetcher = PageBitmapManager('images/pages/{}.pbm'.format(self.page_nbr), 500)
            line_height = self.bitmap_fetcher.image.GetHeight()/len(self.lm.pages[self.page_nbr])
            print line_height
            print self.line.line_nbr
            self.imageCtrl.SetBitmap(self.bitmap_fetcher.get_bitmap(line_height * self.line.line_nbr, 80))
            before_line, after_line = self.lm.line_context(self.page_nbr, self.line)
            text = '\n'.join((before_line, self.line.text, after_line,))
            self.sizeCtrl.SetValue(text)
            self.sizeCtrl.SetStyle(len(before_line), len(before_line) + len(self.line.text) + 1, wx.TextAttr('Black', 'Yellow'))
            self.editCtrl.SetValue(self.line.text)
        else:
            self.sizeCtrl.SetValue('')
            self.editCtrl.SetValue('')

    def set_line_manager(self, line_manager_):
        if line_manager_:
            self.lm = line_manager_
            button = wx.Button(self.panel, wx.ID_ANY, label='Next', size=(60, 20))
            self.Bind(wx.EVT_BUTTON, self.OnNextBadLine, button)
            button.SetDefault()
            button.SetSize(button.GetBestSize())
            # Sizers for layout
            self.current_text.Add(button, row=2, col=1)
            self.panel.SetSizerAndFit(self.current_text)


class PageBitmapManager(object):
    def __init__(self, file_path, desired_width):
        """ Image file path.  If the path does not exist, sets
        itself as a blank (white) image.
        Assumes pbm image (one byte per pixel).
        """
        self.width = desired_width
        bytes_ = []
        try:
            im = Image.open(file_path)
            width, height = im.size
            aspect_ratio = float(height)/width
            still_blank = True
            line_array = []
            for idx, point in enumerate(im.getdata()):
                if still_blank:
                    if len(line_array) == width:
                        avg_point_value = sum(line_array)/width
                        if avg_point_value < 255:
                            still_blank = False
                            for p in line_array:
                                for i in xrange(3):
                                    bytes_.append(point)
                        else:
                            height -= 1
                        line_array = []
                    else:
                        line_array.append(point)
                for i in xrange(3):
                    bytes_.append(point)
        except IOError:
            bytes_ = [255,255,255,]
            aspect_ratio = 1
            width = 1
            height = 1
        bm = wx.BitmapFromBuffer(width, height, array.array('B', bytes_))
        image = wx.ImageFromBitmap(bm)
        self.image = image.Scale(self.width, int(self.width * aspect_ratio), wx.IMAGE_QUALITY_NORMAL)
    def get_bitmap(self, start_height, height):
	image_slice = self.image.GetSubImage(wx.Rect(0, start_height, self.image.GetWidth(), height))
        return wx.BitmapFromImage(image_slice)
        
def main(line_manager_):
    app = App()
    app.set_line_manager(line_manager_)
    app.MainLoop()
if __name__ == '__main__':
    main()

