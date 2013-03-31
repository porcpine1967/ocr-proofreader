#!/usr/bin/env python

import array
import Image

import wx
import wx.lib.rcsizer as rcs

try:
    import aspell
    CAN_ASPELL = True
except ImportError:
    CAN_ASPELL = False

import document_builder
import line_manager
import spell_checker

WIDTH = 800

class App(wx.App):
    def OnInit(self):
        self.line_manager = None
        self.frame = BaseFrame(parent=None, title="Spell Fix", size=(WIDTH, 600))
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True


    def set_line_manager(self, line_manager, strict):
        self.strict = strict
        self.last_page = 0
        self.frame.set_line_manager(line_manager, strict)
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
        self.errors = []
        self.speller = None
        self.strict = False
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
	self.searchCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, '', 
            size=(WIDTH - 100, 40,), style=wx.TE_PROCESS_ENTER)

        self.Bind(wx.EVT_TEXT_ENTER, self.OnEdit, self.editCtrl)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSearch, self.searchCtrl)

        self.current_text.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Page'), row=1, col=1)
        self.current_text.Add(self.pageCtrl, row=1, col=2)
        self.current_text.Add(self.linesCtrl, row=2, col=2, rowspan=4)
        self.current_text.Add(self.errorsCtrl, row=6, col=2)
        self.current_text.Add(self.editCtrl, row=7, col=2)
        self.current_text.Add(self.imageCtrl, row=8, col=2)
        self.current_text.Add(self.searchCtrl, row=9, col=2)

        search_button = wx.Button(self.panel, wx.ID_ANY, label='Search', size=(90, 30))
        self.Bind(wx.EVT_BUTTON, self.OnSearch, search_button)
        search_button.SetDefault()
        search_button.SetSize(search_button.GetBestSize())
        self.current_text.Add(search_button, row=9, col=1)

        self.last_page_callback = None
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        if self.last_page_callback:
            self.last_page_callback(self.page_nbr)
        self.Destroy()

    def OnEdit(self, event):
        self.line.set_text(event.GetString())
        self.OnPreviousLine(None)

    def OnSearch(self, event):
        term = self.searchCtrl.GetValue()
        if term:
            old_page_nbr = self.page_nbr
            self.page_nbr, self.line, self.errors = self.lm.next_value(term, self.page_nbr, self.line)
            self.pageCtrl.SetValue(str(self.page_nbr))
            self.update_line(old_page_nbr)

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
        self.page_nbr, self.line, self.errors = self.lm.next_line_to_check(self.page_nbr, self.line, self.repeating, strict=self.strict)
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)

    def OnJoinLines(self, event):
        if self.line:
            wtvr, next_line = self.lm.next_line(self.page_nbr, self.line)
            if next_line:
                last_word = self.line.pop_last_word()
                next_line.set_text(last_word + next_line.text)
        self.update_line(self.page_nbr)

    def update_line(self, old_page_nbr):
        self.errorsCtrl.SetValue(u', '.join(self.errors))
        if self.line:
#           print self.line.line_nbr
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
            if self.errors:
                try:
                    point = self.line.text.index(self.errors[0]) + len(self.errors[0])
                except ValueError:
                    point = len(self.line.text)
            else:
                point = len(self.line.text)
            self.editCtrl.SetInsertionPoint(point)
        else:
            self.repeating = True
            self.linesCtrl.SetValue('')
            self.editCtrl.SetValue('')

    def set_line_manager(self, line_manager_, strict):
        self.strict = strict
        if line_manager_:
            self.lm = line_manager_
            if CAN_ASPELL:
                self.spell_checker = line_manager_.spell_checker
                self.speller = aspell.Speller('lang', line_manager_.spell_checker.lang)
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

            button_row += 1
            join_line_button = wx.Button(self.panel, wx.ID_ANY, label='Join Lines', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnJoinLines, join_line_button)
            join_line_button.SetDefault()
            join_line_button.SetSize(join_line_button.GetBestSize())
            self.current_text.Add(join_line_button, row=button_row, col=1)

            if self.speller:
                button_row += 1
                add_to_dictionary_button = wx.Button(self.panel, wx.ID_ANY, label='+ to Dict', size=(90, 30))
                self.Bind(wx.EVT_BUTTON, self.OnAddToDict, add_to_dictionary_button)
                add_to_dictionary_button.SetDefault()
                add_to_dictionary_button.SetSize(add_to_dictionary_button.GetBestSize())
                self.current_text.Add(add_to_dictionary_button, row=button_row, col=1)
            # Sizers for layout
            self.panel.SetSizerAndFit(self.current_text)
    def OnAddToDict(self, event):
        if self.line:
            errors = self.spell_checker.check_line(self.line.text)
            for word in errors:
                self.speller.addtoPersonal(word)
            self.speller.saveAllwords()
            self.line.recheck()
            self.OnPreviousLine(None)

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

def main(line_manager_, strict):
    app = App()
    app.set_line_manager(line_manager_, strict)
    app.MainLoop()
    return app
if __name__ == '__main__':
    main()

