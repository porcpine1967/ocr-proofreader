#!/usr/bin/env python
"""
Has html formatting keys, writes html file.

"""
import array
import Image

import wx
import wx.lib.rcsizer as rcs

import line_manager

WIDTH = 800

class App(wx.App):
    def OnInit(self):
        self.line_manager = None
        self.frame = BaseFrame(parent=None, title="Formatter", size=(WIDTH, 600))
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True


    def set_line_manager(self, line_manager_):
        self.last_html_page = 0
        self.last_html_line = 0
        self.frame.set_line_manager(line_manager_)
        self.frame.last_page_callback = self.set_last_page_and_line

    def set_last_page_and_line(self, last_page, last_line):
        self.last_html_page = last_page
        self.last_html_line = last_line

class BaseFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.page_nbr = 0
        self.page_image = None
        self.line = None

	# Make Panel
	self.panel = wx.Panel(self, -1)
        self.current_text = rcs.RowColSizer()
	self.pageCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, str(self.page_nbr), 
            size=(40, 20,), style=wx.TE_READONLY)
	self.linesCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(WIDTH - 100,80,), style=wx.TE_MULTILINE|wx.TE_READONLY)
	self.editCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(WIDTH - 100, 40,), style=wx.TE_PROCESS_ENTER)
        self.imageCtrl = wx.StaticBitmap(self.panel, wx.ID_ANY, 
            wx.BitmapFromBuffer(1,1,array.array('B', (0,0,0,))), size=(WIDTH - 100, 180,)) 


        self.Bind(wx.EVT_TEXT_ENTER, self.OnEdit, self.editCtrl)
        self.current_text.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Page'), row=1, col=1)
        self.current_text.Add(self.pageCtrl, row=1, col=2)
        self.current_text.Add(self.linesCtrl, row=2, col=2, rowspan=4)
        self.current_text.Add(self.editCtrl, row=6, col=2)
        self.current_text.Add(self.imageCtrl, row=7, col=2)

        self.last_page_callback = None
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        if self.last_page_callback and self.line:
            self.last_page_callback(self.page_nbr, self.line.line_nbr)
        self.Destroy()

    def OnEdit(self, event):
        self.line.set_text(event.GetString())
        self.OnNextLine(None)

    def OnPreviousLine(self, event):
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line = self.lm.previous_line(self.page_nbr, self.line)
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)
        
    def OnNextLine(self, event):
        self.errors = []
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line = self.lm.next_line(self.page_nbr, self.line)
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)
        
    def OnJoinLines(self, event):
        if self.line:
            wtvr, next_line = self.lm.next_line(self.page_nbr, self.line)
            if next_line:
                last_word = self.line.pop_last_word()
                next_line.set_text(last_word + next_line.text)
        self.update_line(self.page_nbr)
    def OnAddParagraph(self, event):
        if self.line:
            self.line.set_text(u'<p>{}'.format(self.editCtrl.GetValue()))
            self.OnNextLine(None)
    def OnAddItalParagraph(self, event):
        if self.line:
            self.line.set_text(u'<p style="font-style: italic">{}'.format(self.editCtrl.GetValue()))
            self.OnNextLine(None)
    def OnAddRightAlignParagraph(self, event):
        if self.line:
            self.line.set_text(u'<p style="text-align: right">{}'.format(self.editCtrl.GetValue()))
            self.OnNextLine(None)
    def OnAddHeader(self, event):
        if self.line:
            self.line.set_text(u'<h2>{}</h2>'.format(self.editCtrl.GetValue()))
            self.OnNextLine(None)
 
    def update_line(self, old_page_nbr):
        if self.line:
            if old_page_nbr != self.page_nbr:
                self.page_image = Image.open('images/pages/{}.pbm'.format(self.page_nbr))
            before_line, after_line, idx = self.lm.line_context(self.page_nbr, self.line)
            self.imageCtrl.SetBitmap(pil_image_to_scaled_image(self.line.line_info.image(self.page_image, 
                                                                top=before_line.line_info.y,
                                                                bottom=after_line.line_info.y + after_line.line_info.height), 
                                    WIDTH - 100))
            text = '\n'.join((before_line.text, self.line.text, after_line.text,))
            self.linesCtrl.SetValue(text)
            self.linesCtrl.SetStyle(len(before_line.text), len(before_line.text) + len(self.line.text) + 1, wx.TextAttr('Black', 'Yellow'))
            self.editCtrl.SetValue(self.line.text)
            self.linesCtrl.SetFocus()
            self.editCtrl.SetFocus()
        else:
            self.repeating = True
            self.linesCtrl.SetValue('')
            self.editCtrl.SetValue('')

    def set_line_manager(self, line_manager_):
        if line_manager_:
            self.lm = line_manager_
            button_row = 2

            add_paragraph_button = wx.Button(self.panel, wx.ID_ANY, label='+ <p>', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnAddParagraph, add_paragraph_button)
            add_paragraph_button.SetDefault()
            add_paragraph_button.SetSize(add_paragraph_button.GetBestSize())
            self.current_text.Add(add_paragraph_button, row=button_row, col=1)

            button_row += 1
            add_right_align_paragraph_button = wx.Button(self.panel, wx.ID_ANY, label='+ <p rl>', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnAddRightAlignParagraph, add_right_align_paragraph_button)
            add_right_align_paragraph_button.SetDefault()
            add_right_align_paragraph_button.SetSize(add_right_align_paragraph_button.GetBestSize())
            self.current_text.Add(add_right_align_paragraph_button, row=button_row, col=1)

            button_row += 1
            add_ital_paragraph_button = wx.Button(self.panel, wx.ID_ANY, label='+ <i>', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnAddItalParagraph, add_ital_paragraph_button)
            add_ital_paragraph_button.SetDefault()
            add_ital_paragraph_button.SetSize(add_ital_paragraph_button.GetBestSize())
            self.current_text.Add(add_ital_paragraph_button, row=button_row, col=1)

            button_row += 1
            next_line_button = wx.Button(self.panel, wx.ID_ANY, label='Next Line', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnNextLine, next_line_button)
            next_line_button.SetDefault()
            next_line_button.SetSize(next_line_button.GetBestSize())
            self.current_text.Add(next_line_button, row=button_row, col=1)

            button_row += 1
            previous_line_button = wx.Button(self.panel, wx.ID_ANY, label='Prev Line', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnPreviousLine, previous_line_button)
            previous_line_button.SetDefault()
            previous_line_button.SetSize(previous_line_button.GetBestSize())
            self.current_text.Add(previous_line_button, row=button_row, col=1)

            button_row += 1
            add_header_button = wx.Button(self.panel, wx.ID_ANY, label='header', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnAddHeader, add_header_button)
            add_header_button.SetDefault()
            add_header_button.SetSize(add_header_button.GetBestSize())
            self.current_text.Add(add_header_button, row=button_row, col=1)

            # Sizers for layout
            self.panel.SetSizerAndFit(self.current_text)
            self.OnNextLine(None)

def pil_image_to_scaled_image(pil_image, desired_width):
    bytes_ = []
    for point in pil_image.getdata():
        for i in xrange(3):
            bytes_.append(point)
    width, height = pil_image.size    
    aspect_ratio = float(height)/width
    bm = wx.BitmapFromBuffer(width, height, array.array('B', bytes_))
    full_image = wx.ImageFromBitmap(bm)
    scaled_image = full_image.Scale(desired_width, int(desired_width * aspect_ratio), wx.IMAGE_QUALITY_NORMAL)
    return wx.BitmapFromImage(scaled_image)

def main(line_manager_):
    app = App()
    app.set_line_manager(line_manager_)
    app.MainLoop()
    return app
if __name__ == '__main__':
    main()

