#!/usr/bin/env python

import array
import Image

import wx
import wx.lib.rcsizer as rcs

import document_builder
import line_manager
import spell_checker

WIDTH = 800

class App(wx.App):
    def OnInit(self):
        self.line_manager = None
        self.frame = BaseFrame(parent=None, title="Test App", size=(WIDTH, 600))
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
            size=(WIDTH - 100,80,), style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.current_text.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Page'), row=1, col=1)
	self.editCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(WIDTH - 100, 40,), style=wx.TE_PROCESS_ENTER)
        blank_page_manager = PageBitmapManager('', WIDTH - 100, 1, 1)
        self.imageCtrl = wx.StaticBitmap(self.panel, wx.ID_ANY, 
            blank_page_manager.get_bitmap(80, 80), size=(WIDTH - 100, 180,)) 


        self.Bind(wx.EVT_TEXT_ENTER, self.OnEdit, self.editCtrl)
        self.current_text.Add(self.pageCtrl, row=1, col=2)
        self.current_text.Add(self.sizeCtrl, row=2, col=2, rowspan=4)
        self.current_text.Add(self.editCtrl, row=6, col=2)
        self.current_text.Add(self.imageCtrl, row=7, col=2)

    def OnEdit(self, event):
        self.line.set_text(event.GetString())
        self.OnNextLine(None)

    def OnPreviousLine(self, event):
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line = self.lm.previous_line(self.page_nbr, self.line)
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)
        
    def OnNextLine(self, event):
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line = self.lm.next_line(self.page_nbr, self.line)
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)
        
    def OnNextBadLine(self, event):
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line = self.lm.next_line_to_check(self.page_nbr, self.line)
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)

    def update_line(self, old_page_nbr):
        if self.line:
            if old_page_nbr != self.page_nbr:
                self.bitmap_fetcher = PageBitmapManager('images/pages/{}.pbm'.format(self.page_nbr),
                WIDTH - 100,
                len(self.lm.pages[self.page_nbr]),
                self.lm.average_lines_per_page)
            self.imageCtrl.SetBitmap(self.bitmap_fetcher.get_bitmap(self.line.line_nbr, 180))
            before_line, after_line, idx = self.lm.line_context(self.page_nbr, self.line)
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
            next_error_button = wx.Button(self.panel, wx.ID_ANY, label='Next Error', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnNextBadLine, next_error_button)
            next_error_button.SetDefault()
            next_error_button.SetSize(next_error_button.GetBestSize())
            self.current_text.Add(next_error_button, row=2, col=1)
            next_line_button = wx.Button(self.panel, wx.ID_ANY, label='Next Line', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnNextLine, next_line_button)
            next_line_button.SetDefault()
            next_line_button.SetSize(next_line_button.GetBestSize())
            self.current_text.Add(next_line_button, row=3, col=1)
            previous_line_button = wx.Button(self.panel, wx.ID_ANY, label='Prev Line', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnPreviousLine, previous_line_button)
            previous_line_button.SetDefault()
            previous_line_button.SetSize(previous_line_button.GetBestSize())
            self.current_text.Add(previous_line_button, row=4, col=1)
            # Sizers for layout
            self.panel.SetSizerAndFit(self.current_text)


class PageBitmapManager(object):
    def __init__(self, file_path, desired_width, lines_on_page, lines_per_page):
        """ Image file path.  If the path does not exist, sets
        itself as a blank (white) image.
        Assumes pbm image (one byte per pixel).
        """
        self.lines_on_page = lines_on_page
        self.width = desired_width
        bytes_ = []
        try:
            im = Image.open(file_path)
            width, height = im.size
            rough_line_height = height/lines_per_page
            max_blank_lines = max(rough_line_height/2, 5)
            aspect_ratio = float(height)/width
            line_array = []
            for idx, point in enumerate(im.getdata()):
                line_array.append(point)
                if not len(line_array) % width:
                    avg_point_value = sum(line_array[-width:])/width
                    # has print
                    if avg_point_value < 253:
                        for p in line_array:
                            for i in xrange(3):
                                bytes_.append(p)
                        line_array = []
                    # blank line
                    elif len(line_array)/width > max_blank_lines:
                        line_array = line_array[3*width:]
            height = len(bytes_)/(3*width)
        except IOError:
            bytes_ = [255,255,255,]
            aspect_ratio = 1
            width = 1
            height = 1
        
        bm = wx.BitmapFromBuffer(width, height, array.array('B', bytes_))
        image = wx.ImageFromBitmap(bm)
        self.image = image.Scale(self.width, int(self.width * aspect_ratio), wx.IMAGE_QUALITY_NORMAL)
        self.line_height = self.image.GetHeight()/lines_on_page
    def get_bitmap(self, line_nbr, height):
        start_height = max((0, (line_nbr*self.line_height) - (height/2),))
	image_slice = self.image.GetSubImage(wx.Rect(0, start_height, self.image.GetWidth(), height))
        return wx.BitmapFromImage(image_slice)
        
def main(line_manager_):
    app = App()
    app.set_line_manager(line_manager_)
    app.MainLoop()
if __name__ == '__main__':
    main()

