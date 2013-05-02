#!/usr/bin/env python

import array
import codecs
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
        self.frame = BaseFrame(parent=None, title="Verify Word", size=(WIDTH, 600))
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True

    def set_line_manager(self, line_manager):
        self.frame.set_line_manager(line_manager)

class BaseFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.page_nbr = 0
        self.page_image = None
        self.line = None
        self.repeating = False
        self.words = []
        with codecs.open('working/maybe_ok.txt', mode='rb', encoding='utf-8') as f:
            for l in f:
                self.words.append(l.split()[0])
        self.errors = []
        self.speller = None
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

    def OnEdit(self, event):
        self.line.set_text(event.GetString())
        self.OnPreviousLine(None)

    def OnNextBadLine(self, event):
        old_page_nbr = self.page_nbr
        self.page_nbr, self.line, line_info = self.lm.find_word(self.next_word())
        self.pageCtrl.SetValue(str(self.page_nbr))
        self.update_line(old_page_nbr)

    def next_word(self):
        try:
            self.word = self.words.pop(0)
        except IndexError:
            self.word = ''
        return self.word

    def update_line(self, old_page_nbr):
        self.errorsCtrl.SetValue(self.word)
        if self.line:
            if old_page_nbr != self.page_nbr:
                print 'opening', self.page_nbr
                self.page_image = Image.open('images/pages/{}.pbm'.format(self.page_nbr))
            self.imageCtrl.SetBitmap(pil_image_to_scaled_image(self.line.line_info.image(self.page_image, 1), WIDTH - 100))
            before_line, after_line, idx = self.lm.line_context(self.page_nbr, self.line)
            text = '\n'.join((before_line.text, self.line.text, after_line.text,))
            self.linesCtrl.SetValue(text)
            self.linesCtrl.SetStyle(len(before_line.text), len(before_line.text) + len(self.line.text) + 1, wx.TextAttr('Black', 'Yellow'))
        else:
            print 'not found'
            self.linesCtrl.SetValue('')

    def set_line_manager(self, line_manager_):
        if line_manager_:
            self.lm = line_manager_
            if CAN_ASPELL:
                self.spell_checker = line_manager_.spell_checker
                print line_manager_.spell_checker.lang
                self.speller = aspell.Speller('lang', line_manager_.spell_checker.lang)

            next_error_button = wx.Button(self.panel, wx.ID_ANY, label='Next Error', size=(90, 30))
            self.Bind(wx.EVT_BUTTON, self.OnNextBadLine, next_error_button)
            next_error_button.SetDefault()
            next_error_button.SetSize(next_error_button.GetBestSize())
            self.current_text.Add(next_error_button, row=2, col=1)

            if self.speller:
                add_to_dictionary_button = wx.Button(self.panel, wx.ID_ANY, label='+ to Dict', size=(90, 30))
                self.Bind(wx.EVT_BUTTON, self.OnAddToDict, add_to_dictionary_button)
                add_to_dictionary_button.SetDefault()
                add_to_dictionary_button.SetSize(add_to_dictionary_button.GetBestSize())
                self.current_text.Add(add_to_dictionary_button, row=5, col=1)
            # Sizers for layout
            self.panel.SetSizerAndFit(self.current_text)
    def OnAddToDict(self, event):
        if self.word:
            self.speller.addtoPersonal(self.word)
            self.speller.saveAllwords()
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
if __name__ == '__main__':
    main()

