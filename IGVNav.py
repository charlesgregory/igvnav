import os
import sys
import csv
import wx
import socket

TEST_MODE=False


variant_call_tool_tips = {
'A': "Ambiguous, variant could or could not be real",
'F': "Fail, variant failed manual review",
'G': "Germline, variant is a real germline variant",
'S': "Somatic, variant is a real somatic variant",
}

variant_tag_tool_tips = {
'AI': "Adjacent Indel, variant likely due to misalignment of an adjacent indel",
'HDR': "High Discrepancy Region, Dirty Region, Region contains many reads with multiple mismatches",
'MM': "Multiple Mismatches, Reads with variant contain multiple mismatches from reference",
'MV': "Multiple Variants, More than 1 non-reference variant at the same base location",
'MN': "MonoNucleotide run, Region contains pattern of repeat ex. AAAAAA",
'DN': "DiNucleotide run, Region contains pattern of repeat ex. AGAGAG",
'TR': "Tandem Repeat, Region contains pattern of repeat ex. ACGACGACG",
'LCT': "Low Coverage in Tumor, Region contains low coverage in tumor",
'LCN': "Low Coverage in Normal, Region contains low coverage in normal",
'NCN': "No Coverage in Normal, Region contains no coverage in normal",
'TN': "Tumor in Normal, Variant support in normal (common in blood cancers)",
'LVF': "Low Variant Allele Frequency, Variant has a low VAF",
'LM': "Low Mapping quality, Reads are poorly mapped",
'SI': "Short Insert, Reads contain short inserts",
'SIO': "Short Insert Only,  Reads contain only short inserts",
'SSE': "Same Start/END,  Short reads have same start or end points",
'D': "Directional reads, Majority of reads are in the same direction",
'E': "End of reads, Variant only supported by the end of reads",
'AO': "Ambiguous Other, Provide an explanation not otherwise specified here",
'MS': "Multiple Samples, Variant appears in multiple samples",
'HC':"Hard-clipped, Reads containing variant are hard-clipped",
'TO':"Tumor-only, No germline available",
'SB':"Strand Bias, variant is found on reads of only one strand",
'LQ':"Low quality, variant reads are of low base quality",
'BIR':"Flag for Bioinformatics Review",
'IDK':"I don't know what to call"
}

class IGV_Socket(object):
    def __init__(self):
        self.base = 0

    def set_base(self, base):
        self.base = base

    def set_port(self, port):
        self.port=port

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect( ("127.0.0.1", self.port) )

    def send_cmd(self, cmd):
        totalsent = 0
        while totalsent < len(cmd):
            sent = self.sock.send(cmd[totalsent:])
            if sent == 0:
                raise Exception("Socket connection broken")
            totalsent = totalsent + sent

    def recv(self):
        chunk = self.sock.recv(4096)
        if chunk == '':
            raise Exception("Socket connection broken")
        return chunk

    def goto_variant(self, chromosome, start, ref):
        position = start
        if self.base == 1:
            if (ref == '-' or ref =='0' or ref == ''):
                print "Found insert, going forward by one"
                position += 1

        self.goto(chromosome, position)

    def goto(self, chromosome, position):
        if TEST_MODE:
            return
        position = position - self.base

        print "SEND: goto %s:%d" % (chromosome, position)

        self.connect()
        self.send_cmd("goto %s:%d\n" % (chromosome, position))
        self.recv()
        self.send_cmd("sort base\n")
        self.recv()
        self.close()

    def sort(self):
        if TEST_MODE:
            return

        self.connect()
        self.send_cmd("sort base\n")
        self.recv()
        self.close()

    def close(self):
        self.sock.close()

class ReviewWidget(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(ReviewWidget, self).__init__(*args, **kwargs)
        self.bedfile = None
        self.igvsock = None
        self.font=wx.Font(14,wx.DECORATIVE,wx.ITALIC,wx.NORMAL)
        self.InitUI()
    def setBedFile(self, bedfile):
        self.bedfile = bedfile

    def setSocket(self, sock):
        self.igvsock = sock

    def CreateMenus(self):
        ID_FILE_OPEN = wx.NewId()
        ID_FILE_SAVE = wx.NewId()
        ID_FILE_EXIT = wx.NewId()

        file_menu = wx.Menu()
        file_menu.Append(ID_FILE_OPEN, 'Open File')
        file_menu.Append(ID_FILE_SAVE, 'Save File')
        file_menu.Append(ID_FILE_EXIT, 'Quit')

        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, 'File')
        self.SetMenuBar(menu_bar)

        wx.EVT_MENU(self, ID_FILE_OPEN, self.OnOpen)
        wx.EVT_MENU(self, ID_FILE_SAVE, self.OnSave)
        wx.EVT_MENU(self, ID_FILE_EXIT, self.OnQuit)

    def SetBase(self, e):
        base = 1 if self.isbase1.GetValue() else 0
        print "Setting base:", base
        self.igvsock.set_base( base )

    def InitUI(self):
        self.CreateMenus()
        padd=5
        framelayout = wx.BoxSizer(wx.VERTICAL)
        self.filenameText = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.isbase1 = wx.CheckBox(self, label='1-Base?')
        self.isbase1.SetFont(self.font)

        framelayout.Add(self.filenameText, 0, wx.EXPAND, 0)
        framelayout.Add(self.isbase1, 0, wx.EXPAND | wx.ALL, padd)

        self.isbase1.Bind(wx.EVT_CHECKBOX, self.SetBase)

        navpanel = self.createNavPanel()

        framelayout.Add(navpanel, 0,wx.ALL,padd)
        variant=wx.StaticText( self, label="Variant" )
        variant.SetFont(self.font)
        framelayout.Add( variant, 0, wx.EXPAND |wx.LEFT, padd)

        varpanel = self.createVarNumPanel()
        framelayout.Add(varpanel, 0,wx.ALL,padd)

        self.posText = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.refText = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.varText = wx.TextCtrl(self, style=wx.TE_READONLY)

        self.posText.SetFont(self.font)
        self.refText.SetFont(self.font)
        self.varText.SetFont(self.font)


        framelayout.Add(self.posText, 0, wx.EXPAND | wx.ALL, padd)
        framelayout.Add(self.refText, 0, wx.EXPAND | wx.ALL, padd)
        framelayout.Add(self.varText, 0, wx.EXPAND | wx.ALL, padd)
        call=wx.StaticText( self, label="Call" )
        call.SetFont(self.font)
        framelayout.Add( call, 0, wx.EXPAND | wx.LEFT, padd)

        callpanel = self.createCallPanel()
        framelayout.Add(callpanel, 0,0,0)
        tags=wx.StaticText( self, label="Tags" )
        tags.SetFont(self.font)
        framelayout.Add( tags, 0, wx.EXPAND | wx.LEFT, padd)
        tagspanel = self.createTagsPanel()
        framelayout.Add(tagspanel, 0,wx.EXPAND,0)
        notes=wx.StaticText( self, label="Notes" )
        notes.SetFont(self.font)
        framelayout.Add( notes, 0, wx.EXPAND | wx.LEFT, padd)
        self.notesText = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1,200))
        self.notesText.SetFont(self.font)
        self.notesText.Bind( wx.EVT_TEXT, self.NotesChanged )

        framelayout.Add( self.notesText, 0, wx.EXPAND, 0 )
        savebutton = wx.Button(self, -1, label='Save')
        savebutton.Bind(wx.EVT_BUTTON, self.OnSave)
        framelayout.Add( savebutton, 0, wx.EXPAND | wx.ALL, padd )

        self.SetSizer(framelayout)
        framelayout.SetSizeHints(self)
        self.Show(True)

        wx.ToolTip.SetDelay(20)


    def OnSave(self, e):
        self.bedfile.save()

    def goToVar(self, e):
        try:
            pos = int( self.numText.GetValue() )
            if pos < 1:
                raise Exception("Invalid position: " + pos)
            if pos > self.bedfile.num_vars():
                raise Exception("Invalid position: " + pos)

            self.chromosome, self.position = self.bedfile.set_cursor_pos(pos-1)
            self.gotoPos()
        except e:
            print e.msg
            pass

        self.refresh()

    def createVarNumPanel(self):
        padd=5
        varpanel = wx.Panel(self)
        varlayout = wx.BoxSizer(wx.HORIZONTAL)
        pound=wx.StaticText( varpanel, label="#" )
        font=wx.Font(18,wx.DECORATIVE,wx.ITALIC,wx.NORMAL)
        pound.SetFont(font)
        varlayout.Add( pound, 0, wx.RIGHT, padd)

        self.numText = wx.TextCtrl(varpanel, size=(50,-1))
        self.totText = wx.TextCtrl(varpanel, style=wx.TE_READONLY, size=(50,-1))

        varlayout.Add( self.numText, 0, 0, 0)
        slash=wx.StaticText( varpanel, label="/" )
        slash.SetFont(font)
        varlayout.Add( slash, 0, wx.LEFT|wx.RIGHT, padd)
        varlayout.Add( self.totText, 0, 0, 0)

        self.gotoVarButton = wx.Button(varpanel, -1, label="Go", style=wx.BU_EXACTFIT)
        self.gotoVarButton.SetFont(self.font)
        self.gotoVarButton.Bind(wx.EVT_BUTTON, self.goToVar)

        varlayout.Add( self.gotoVarButton, 0, 0, 0)

        varpanel.SetSizer(varlayout)
        varlayout.SetSizeHints(varpanel)

        return varpanel

    def createCallPanel(self):
        padd=5
        callpanel = wx.Panel(self)
        calllayout = wx.BoxSizer(wx.HORIZONTAL)

        sombutton = wx.ToggleButton(callpanel, -1, label='S', style=wx.BU_EXACTFIT)
        germbutton = wx.ToggleButton(callpanel, -1, label='G', style=wx.BU_EXACTFIT)
        ambbutton = wx.ToggleButton(callpanel, -1, label='A', style=wx.BU_EXACTFIT)
        failbutton = wx.ToggleButton(callpanel, -1, label='F', style=wx.BU_EXACTFIT)

        sombutton.SetFont(self.font)
        germbutton.SetFont(self.font)
        ambbutton.SetFont(self.font)
        failbutton.SetFont(self.font)
        calllayout.Add(sombutton, 0,wx.LEFT | wx.RIGHT, padd)
        calllayout.Add(germbutton, 0,wx.LEFT | wx.RIGHT, padd)
        calllayout.Add(ambbutton, 0,wx.LEFT | wx.RIGHT, padd)
        calllayout.Add(failbutton, 0,wx.LEFT | wx.RIGHT, padd)

        sombutton.SetToolTip(wx.ToolTip(variant_call_tool_tips['S']))
        germbutton.SetToolTip(wx.ToolTip(variant_call_tool_tips['G']))
        ambbutton.SetToolTip(wx.ToolTip(variant_call_tool_tips['A']))
        failbutton.SetToolTip(wx.ToolTip(variant_call_tool_tips['F']))

        sombutton.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self.ChooseCall('S'))
        germbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self.ChooseCall('G'))
        ambbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self.ChooseCall('A'))
        failbutton.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self.ChooseCall('F'))

        callpanel.SetSizer(calllayout)
        calllayout.SetSizeHints(callpanel)

        self.callbuttons = {'S': sombutton, 'G': germbutton, 'A': ambbutton, 'F': failbutton}

        return callpanel

    def createTagsPanel(self):
        padd=5
        self.tag_buttons = {}
        variant_tags = sorted( list( variant_tag_tool_tips.keys() ) )

        bpanel = wx.Panel(self,size=(-1, 35*len(variant_tags)/3))
        blayout = wx.WrapSizer(wx.HORIZONTAL)

        for tag in variant_tags:
            tooltip = variant_tag_tool_tips[tag]

            tag_button = wx.ToggleButton( bpanel, -1, label=tag, style=wx.BU_EXACTFIT )

            if tag=="BIR":
                tag_button.SetBackgroundColour(wx.Colour(0, 100, 200))
            elif tag=="IDK":
                tag_button.SetBackgroundColour(wx.Colour(255, 0, 0))

            tag_button.SetFont(self.font)

            tag_button.SetToolTip( wx.ToolTip( tooltip ) )
            tag_button.Bind(wx.EVT_TOGGLEBUTTON, self.ChooseTags )

            blayout.Add(tag_button, 0, wx.ALL, padd)

            self.tag_buttons[tag] = tag_button

        bpanel.SetSizer(blayout)
#        blayout.SetSizeHints(bpanel)

        return bpanel


    def createNavPanel(self):
        navpanel = wx.Panel(self)
        navlayout = wx.BoxSizer(wx.HORIZONTAL)

        firstbtn = wx.Button(navpanel, -1, label='|<', style=wx.BU_EXACTFIT)
        prevbtn = wx.Button(navpanel, -1, label='<<', style=wx.BU_EXACTFIT)
        backbtn = wx.Button(navpanel, -1, label='<', style=wx.BU_EXACTFIT)
        fwdbtn = wx.Button(navpanel, -1, label='>', style=wx.BU_EXACTFIT)
        nextbtn = wx.Button(navpanel, -1, label='>>', style=wx.BU_EXACTFIT)
        lastbtn = wx.Button(navpanel, -1, label='>|', style=wx.BU_EXACTFIT)
        sortbtn = wx.Button(navpanel, -1, label="S", style=wx.BU_EXACTFIT)

        firstbtn.SetFont(self.font)
        prevbtn.SetFont(self.font)
        backbtn.SetFont(self.font)
        fwdbtn.SetFont(self.font)
        nextbtn.SetFont(self.font)
        lastbtn.SetFont(self.font)
        sortbtn.SetFont(self.font)

        navlayout.Add(firstbtn, 0,0,0)
        navlayout.Add(prevbtn, 0,0,0)
        navlayout.Add(backbtn, 0,0,0)
        navlayout.Add(fwdbtn, 0,0,0)
        navlayout.Add(nextbtn, 0,0,0)
        navlayout.Add(lastbtn, 0,0,0)
        navlayout.Add(sortbtn, 0,0,0)

        firstbtn.Bind(wx.EVT_BUTTON, self.OnFirst)
        prevbtn.Bind(wx.EVT_BUTTON, self.OnPrevious)
        backbtn.Bind(wx.EVT_BUTTON, self.OnBack)
        fwdbtn.Bind(wx.EVT_BUTTON, self.OnForward)
        nextbtn.Bind(wx.EVT_BUTTON, self.OnNext)
        lastbtn.Bind(wx.EVT_BUTTON, self.OnLast)
        sortbtn.Bind(wx.EVT_BUTTON, self.OnSort)

        navpanel.SetSizer(navlayout)
        navlayout.SetSizeHints(navpanel)
        return navpanel

    def refresh(self):
        self.filenameText.SetValue( self.bedfile.filename )

        pos = self.bedfile.get_pos()
        ref = self.bedfile.get_ref()
        var = self.bedfile.get_var()

        cp = self.bedfile.get_cp()
        count = self.bedfile.num_vars()

        self.posText.SetValue(pos)
        self.refText.SetValue(ref)
        self.varText.SetValue(var)

        self.numText.SetValue("%d" % (cp+1))
        self.totText.SetValue("%d" % (count))

        call = self.bedfile.get_call()
        for c in self.callbuttons:
            if c == call:
                self.callbuttons[c].SetValue(True)
            else:
                self.callbuttons[c].SetValue(False)

        for t in self.tag_buttons:
            if self.bedfile.has_tag(t):
                self.tag_buttons[t].SetValue(True)
            else:
                self.tag_buttons[t].SetValue(False)

        self.notesText.SetValue( self.bedfile.get_notes() )


    def ChooseTags(self, event):
        for t in self.tag_buttons:
            if self.tag_buttons[t].GetValue():
                self.bedfile.set_tag(t)
            else:
                self.bedfile.unset_tag(t)
        self.refresh()

    def ChooseCall(self, call):
        self.bedfile.set_call(call)
        self.refresh()

    def NotesChanged(self, e):
        notes = self.notesText.GetValue()
        self.bedfile.set_notes( notes )

    def gotoPos(self):
        self.igvsock.goto_variant( self.chromosome, self.position, self.bedfile.get_ref() )

    def OnSort(self, e):
        self.igvsock.sort( )

    def OnFirst(self, e):
        self.chromosome, self.position = self.bedfile.first_var()
        self.refresh()
        self.gotoPos()

    def OnPrevious(self, e):
        if self.bedfile.has_prev():
            self.chromosome, self.position = self.bedfile.prev_var()
            self.refresh()
            self.gotoPos()

    def OnBack(self, e):
        self.position-=1
        self.gotoPos()

    def OnForward(self, e):
        self.position+=1
        self.gotoPos()

    def OnNext(self, e):
        if self.bedfile.has_next():
            self.chromosome, self.position = self.bedfile.next_var()
            self.refresh()
            self.gotoPos()

    def OnLast(self, e):
        self.chromosome, self.position = self.bedfile.last_var()
        self.refresh()
        self.gotoPos()

    def OnQuit(self, e):
        self.Close()

    def OnOpen(self, e):
        openFileDialog = wx.FileDialog(self, "Open variant file", "", "", "Variant files (*.csv;*.tsv;*.txt;*.bed)|*.csv;*.tsv;*.txt;*.bed",
                                                       wx.FD_OPEN |
                                                       wx.FD_FILE_MUST_EXIST)

        if openFileDialog.ShowModal() == wx.ID_CANCEL:
            if self.bedfile is None:
                self.Close()
            return

        bed_file = BedFile( openFileDialog.GetPath() )
        bed_file.load()

        self.setBedFile(bed_file)
        self.OnFirst(None)


class BedFile(object):

    def __init__(self, fpath, has_header=None):
        self.filepath = fpath
        self.filename = fpath.split(os.sep)[-1]
        self.has_header = has_header
        self.data = []
        self.cursor_pos = -1

    def save(self):
        fpath = self.filepath
        if TEST_MODE:
            fpath += ".test.tsv"

        with open(fpath, 'w') as bfile:
            cw = csv.writer(bfile, dialect='excel-tab', quotechar="\"")

            cw.writerow(["Chromosome", "Start", "Stop", "Reference", "Variant", "Call", "Tags", "Notes"])
            for datarow in self.data:
                cw.writerow(datarow['data'])

    def load(self):
        with open(self.filepath, 'rU') as bfile:
            cr = csv.reader(bfile, dialect='excel-tab', quotechar="\"")
            i = 0
            for row in cr:
                if i == 0:
                    if self.has_header:
                        i += 1
                        continue
                    elif self.has_header is None:
                        try:
                            int(row[1])
                            int(row[2])
                        except ValueError:
                            self.has_header = True
                            i += 1
                            continue
                        else:
                            self.has_header = False

                chromosome = row[0]
                start, stop = int(row[1]), int(row[2])
                ref, var = row[3], row[4]
                call, tags, notes = "", [], ""
                if len(row) > 5:
                    call = row[5]
                if len(row) > 6:
                    tags = [ t.strip() for t in row[6].split(",") if len(t.strip())>0 ]
                if len(row) > 7:
                    notes = row[7]

                self.append( chromosome, start, stop, ref, var, call, tags, notes, row )
                i += 1

    def first_var(self):
        self.cursor_pos = 0
        return self.data[self.cursor_pos]['chr'], self.data[self.cursor_pos]['start']

    def last_var(self):
        self.cursor_pos = len(self.data)-1
        return self.data[self.cursor_pos]['chr'], self.data[self.cursor_pos]['start']

    def set_cursor_pos(self, pos):
        self.cursor_pos = pos
        return self.data[self.cursor_pos]['chr'], self.data[self.cursor_pos]['start']

    def has_next(self):
        return self.cursor_pos < len(self.data) - 1

    def has_prev(self):
        return self.cursor_pos > 0

    def next_var(self):
        if self.cursor_pos < len(self.data) - 1:
            self.cursor_pos += 1
        return self.data[self.cursor_pos]['chr'], self.data[self.cursor_pos]['start']

    def prev_var(self):
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
        return self.data[self.cursor_pos]['chr'], self.data[self.cursor_pos]['start']

    def get_pos(self):
        return "%s:%d-%d" % ( self.data[self.cursor_pos]['chr'],
                self.data[self.cursor_pos]['start'],
                self.data[self.cursor_pos]['stop'])

    def get_cp(self):
        return self.cursor_pos

    def num_vars(self):
        return len(self.data)

    def get_ref(self):
        return self.data[self.cursor_pos]['ref']

    def get_var(self):
        return self.data[self.cursor_pos]['var']

    def get_call(self):
        return self.data[self.cursor_pos]['call']

    def set_call(self, call):
        self.data[self.cursor_pos]['call'] = call
        self.data[self.cursor_pos]['data'][5] = call

    def has_tag(self, tag):
        return tag in self.data[self.cursor_pos]['tags']

    def set_tag(self, tag):
        if tag not in self.data[self.cursor_pos]['tags']:
            self.data[self.cursor_pos]['tags'].append(tag)

        self.data[self.cursor_pos]['data'][6] = ', '.join(self.data[self.cursor_pos]['tags'])

    def unset_tag(self, tag):
        if tag in self.data[self.cursor_pos]['tags']:
            self.data[self.cursor_pos]['tags'].remove(tag)

        self.data[self.cursor_pos]['data'][6] = ', '.join(self.data[self.cursor_pos]['tags'])

    def get_notes(self):
        return self.data[self.cursor_pos]['notes']

    def set_notes(self, notes):
        self.data[self.cursor_pos]['notes'] = notes
        self.data[self.cursor_pos]['data'][7] = notes

    def append(self, chromosome, start, stop, ref, var, call, tags, notes, data):
        if call != "" and call not in variant_call_tool_tips:
            raise Exception("Invalid variant call: " + call)
        for t in tags:
            if t not in variant_tag_tool_tips:
                raise Exception("Invalid variant tag: " + t)

        while len(data) < 8:
            data.append("")

        self.data.append( {'chr': chromosome, 'start': start, 'stop': stop,
                            'ref': ref, 'var': var,
                            'call': call, 'tags': tags, 'notes': notes,
                            'data':data} )


def main(*args):
    app = wx.App()
    port=args[0][1]
    sock=IGV_Socket()
    sock.set_port(port)
    rw = ReviewWidget(None)
    rw.setSocket(sock)
    rw.OnOpen(None)

    app.MainLoop()


if __name__ == '__main__':
    main(sys.argv)
