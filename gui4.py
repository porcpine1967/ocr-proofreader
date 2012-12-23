#!/usr/bin/env python
"""
Checks for odd orthography vis-a-vis proper nouns.
"""
import array
import codecs
import Image

import wx
import wx.lib.rcsizer as rcs


import document_builder
import line_manager

WIDTH = 800

class App(wx.App):
    def OnInit(self):
        self.line_manager = None
        self.frame = BaseFrame(parent=None, title="Verify Word", size=(WIDTH, 600))
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True

    def set_line_manager(self, line_manager):
        self.frame.set_line_manager(line_manager)
        self.last_page = 0
        self.frame.last_page_callback = self.set_last_page

    def set_last_page(self, last_page):
        self.last_page = last_page

class BaseFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.page_nbr = 0
        self.page_image = None
        self.line = None
        self.repeating = False
        self.proper_nouns = set()
        with codecs.open('working/proper_nouns.txt', mode='ab', encoding='utf-8') as f:
            pass
        with codecs.open('working/proper_nouns.txt', mode='rb', encoding='utf-8') as f:
            for l in f:
                line = l.strip()
                if line:
                    self.proper_nouns.add(line)

        self.errors = []
	# Make Panel
	self.panel = wx.Panel(self, -1)
        self.current_text = rcs.RowColSizer()
	self.pageCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, str(self.page_nbr), 
            size=(40, 20,), style=wx.TE_READONLY)
	self.linesCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(WIDTH - 100,80,), style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.errorsCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '',
            size=(WIDTH - 100, 40), style=wx.TE_READONLY)
	self.editCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(WIDTH - 100, 40,), style=wx.TE_PROCESS_ENTER)
        self.imageCtrl = wx.StaticBitmap(self.panel, wx.ID_ANY, 
            wx.BitmapFromBuffer(1,1,array.array('B', (0,0,0,))), size=(WIDTH - 100, 180,)) 


        self.Bind(wx.EVT_TEXT_ENTER, self.OnEdit, self.editCtrl)
        self.current_text.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Page'), row=1, col=1)
        self.current_text.Add(self.pageCtrl, row=1, col=2)
        self.current_text.Add(self.linesCtrl, row=2, col=2, rowspan=4)
        self.current_text.Add(self.errorsCtrl, row=6, col=2)
        self.current_text.Add(self.editCtrl, row=7, col=2)
        self.current_text.Add(self.imageCtrl, row=8, col=2)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        with codecs.open('working/proper_nouns.txt', mode='wb', encoding='utf-8') as f:
            for word in self.proper_nouns:
                f.write(u'{}\n'.format(word))
        self.last_page_callback(self.page_nbr)
        self.Destroy()

    def OnEdit(self, event):
        self.line.set_text(event.GetString())
        self.OnPreviousLine(None)

    def OnPreviousLine(self, event):
        self.errors = []
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

    def OnNextBadLine(self, event):
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line, self.possible_proper_nouns = self.lm.next_proper_noun(self.page_nbr, self.line, self.proper_nouns)
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)

    def update_line(self, old_page_nbr):
        self.errorsCtrl.SetValue(' '.join(self.possible_proper_nouns))
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
            if self.possible_proper_nouns:
                try:
                    point = self.line.text.index(self.possible_proper_nouns[0]) + len(self.possible_proper_nouns[0])
                except ValueError:
                    point = len(self.line.text)
            else:
                point = len(self.line.text)
            self.editCtrl.SetInsertionPoint(point)
        else:
            self.repeating = True
            self.linesCtrl.SetValue('')

    def set_line_manager(self, line_manager_):
        if line_manager_:
            self.lm = line_manager_

            button_row = 2
            next_error_button = wx.Button(self.panel, wx.ID_ANY, label='Next Error', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnNextBadLine, next_error_button)
            next_error_button.SetDefault()
            next_error_button.SetSize(next_error_button.GetBestSize())
            self.current_text.Add(next_error_button, row=button_row, col=1)


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

            button_row += 2
            add_to_proper_button = wx.Button(self.panel, wx.ID_ANY, label='Proper', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnAddToProper, add_to_proper_button)
            add_to_proper_button.SetDefault()
            add_to_proper_button.SetSize(add_to_proper_button.GetBestSize())
            self.current_text.Add(add_to_proper_button, row=button_row, col=1)
            # Sizers for layout
            self.panel.SetSizerAndFit(self.current_text)

    def OnAddToProper(self, event):
        for word in self.possible_proper_nouns:
            self.proper_nouns.add(self.lm.spell_checker.strip_garbage(word))
        self.possible_proper_nouns = []
        self.OnNextBadLine(None)

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

