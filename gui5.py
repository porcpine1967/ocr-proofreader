#!/usr/bin/env python
"""
GUI for manipulating page info
"""
import array
import Image, ImageDraw
import csv

import wx
import wx.lib.rcsizer as rcs

from document_builder import LineInfo

WIDTH = 800
IMG_HEIGHT = 180
class App(wx.App):
    def OnInit(self):
        self.frame = BaseFrame(parent=None, title="Page Info Fix", size=(WIDTH, 600))
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True
       
    def set_page_nbr(self, page_nbr):
        self.page_nbr = page_nbr
        self.frame.image = Image.open('images/pages/{}.pbm'.format(page_nbr)).convert('RGB')
        self.frame.page_nbr = page_nbr

        self.frame.line_infos = []
        with open('working/page_info/{}.csv'.format(page_nbr), 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                line_info = LineInfo(int(row[3]))
                line_info.height = int(row[1])
                line_info.left_margin = int(row[2])
                line_info.width = int(row[4])
                self.frame.line_infos.append(line_info)
        self.frame.show_panel()

class BaseFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.image = None
        self.line_infos = []
        self.current_line = 0
        self.current_height = 0
        self.width = WIDTH - 100
        self.scroll_change = 5
        self.page_nbr = 0

    def OnScrollDown(self, event):
        self.current_height += self.scroll_change
        self.set_image()

    def OnScrollUp(self, event):
        self.current_height -= self.scroll_change
        self.set_image()

    def OnNextLine(self, event):
        self.current_line += 1
        self.maybe_correct_height()
        self.set_image()

    def OnPrevLine(self, event):
        self.current_line -= 1
        self.maybe_correct_height()
        self.set_image()

    def OnRemoveLine(self, event):
        self.line_infos.pop(self.current_line)
        if self.current_line + 1 > len(self.line_infos):
            self.current_line -= 1
        self.set_image()

    def OnAddLine(self, event):
        new_line_y = self.current_height + (IMG_HEIGHT / 2)
        line_info = LineInfo(new_line_y)
        inserted = False
        for idx, li in enumerate(self.line_infos):
            if li.y > new_line_y:
                self.line_infos.insert(idx, line_info)
                inserted = True
                break
        if not inserted:
            self.line_infos.append(line_info)
        self.set_image()

    def OnWriteLineInfos(self, event):
        width, height = self.image.size
        with open('working/page_info/{}.csv'.format(self.page_nbr), 'w') as f:
            writer = csv.writer(f)
            line_height = 10
            for idx, line_info in enumerate(self.line_infos):
                if idx + 1 < len(self.line_infos):
                    line_height = self.line_infos[idx + 1].y - line_info.y
                writer.writerow([self.page_nbr, line_height, 0, line_info.y, width])

    def maybe_correct_height(self):
        line_info = self.line_infos[self.current_line]
        self.current_height = line_info.y - (IMG_HEIGHT / 2)

    def set_image(self):
        """ Sets the image in the image control to current scroll and line."""
        self.imageCtrl.SetBitmap(
            self.scaled_image())

    def scaled_image(self):
        width, height = self.image.size
        return pil_image_to_scaled_image(self.draw_lines().crop((0, self.current_height, width, self.current_height + IMG_HEIGHT,)),
           self.width)

    def draw_lines(self):
        """ Returns copy of image with lines on it."""    
        im = self.image.copy()
        d = ImageDraw.Draw(im)
        width, height = im.size
        for idx, line_info in enumerate(self.line_infos):
            if idx == self.current_line:
                d.line((0, line_info.y, width, line_info.y,), fill='red', width=3)
            else:
                d.line((0, line_info.y, width, line_info.y,), fill='black', width=3)
        midline = self.current_height + (IMG_HEIGHT / 2)
        d.line((0, midline, width / 4, midline), fill='blue', width=4)
        return im 

    def show_panel(self):
	# Make Panel
	self.panel = wx.Panel(self, -1)
        self.layout = rcs.RowColSizer()
        button_row = 0

        button_row += 1
        scroll_up_button = wx.Button(self.panel, wx.ID_ANY, label='Scroll Up', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnScrollUp, scroll_up_button)
        scroll_up_button.SetDefault()
        scroll_up_button.SetSize(scroll_up_button.GetBestSize())
        self.layout.Add(scroll_up_button, row=button_row, col=1)

        button_row += 1
        scroll_down_button = wx.Button(self.panel, wx.ID_ANY, label='Scroll Down', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnScrollDown, scroll_down_button)
        scroll_down_button.SetDefault()
        scroll_down_button.SetSize(scroll_down_button.GetBestSize())
        self.layout.Add(scroll_down_button, row=button_row, col=1)

        button_row += 2
        next_line_button = wx.Button(self.panel, wx.ID_ANY, label='Next Line', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnNextLine, next_line_button)
        next_line_button.SetDefault()
        next_line_button.SetSize(next_line_button.GetBestSize())
        self.layout.Add(next_line_button, row=button_row, col=1)

        button_row += 1
        prev_line_button = wx.Button(self.panel, wx.ID_ANY, label='Prev Line', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnPrevLine, prev_line_button)
        prev_line_button.SetDefault()
        prev_line_button.SetSize(prev_line_button.GetBestSize())
        self.layout.Add(prev_line_button, row=button_row, col=1)

        button_row += 2
        remove_line_button = wx.Button(self.panel, wx.ID_ANY, label='Remove Line', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnRemoveLine, remove_line_button)
        remove_line_button.SetDefault()
        remove_line_button.SetSize(remove_line_button.GetBestSize())
        self.layout.Add(remove_line_button, row=button_row, col=1)

        button_row += 1
        add_line_button = wx.Button(self.panel, wx.ID_ANY, label='Add Line', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnAddLine, add_line_button)
        add_line_button.SetDefault()
        add_line_button.SetSize(add_line_button.GetBestSize())
        self.layout.Add(add_line_button, row=button_row, col=1)

        button_row += 4
        write_line_infos_button = wx.Button(self.panel, wx.ID_ANY, label='Write', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnWriteLineInfos, write_line_infos_button)
        write_line_infos_button.SetDefault()
        write_line_infos_button.SetSize(add_line_button.GetBestSize())
        self.layout.Add(write_line_infos_button, row=button_row, col=1)

        self.imageCtrl = wx.StaticBitmap(self.panel, wx.ID_ANY, 
            self.scaled_image(), size=(self.width, IMG_HEIGHT,)) 
        self.layout.Add(self.imageCtrl, row=8, col=2)
        self.panel.SetSizerAndFit(self.layout)
        
def pil_image_to_scaled_image(pil_image, desired_width):
    bytes_ = [item for points in pil_image.getdata() for item in points]
    width, height = pil_image.size    
    aspect_ratio = float(height)/width
    bm = wx.BitmapFromBuffer(width, height, array.array('B', bytes_))
    full_image = wx.ImageFromBitmap(bm)
    scaled_image = full_image.Scale(desired_width, int(desired_width * aspect_ratio), wx.IMAGE_QUALITY_NORMAL)
    return wx.BitmapFromImage(scaled_image)

def main(page_nbr):
    app = App()
    app.set_page_nbr(page_nbr)
    app.MainLoop()
    return app

if __name__ == '__main__':
    main(236)
