#!/usr/bin/python
#
# wx panel widget for Epics Motor
#
# makes use of these modules
#    wxlib:  extensions of wx.TextCtrl, etc for epics PVs
#    Motor:  Epics Motor class
#
#  Aug 21 2004 MN
#         initial working version.
#----------------------------------------
import wx
import sys
import epics
from epics.wx.wxlib import pvText, pvFloatCtrl, pvTextCtrl, \
     DelayedEpicsCallback, EpicsFunction, set_float

from epics.wx.MotorDetailFrame  import MotorDetailFrame

class MotorPanel(wx.Panel):
    """ MotorPanel  a simple wx windows panel for controlling an Epics Motor
    """
    __motor_fields = ('set', 'enabled', 'low_limit','high_limit',
                      'soft_limit','tweak_val',
                      'high_limit_set', 'low_limit_set', 'stop_go')

    def __init__(self, parent,  motor=None,  
                 style='normal', messenger=None, *args, **kw):

        wx.Panel.__init__(self, parent, style=wx.TAB_TRAVERSAL)
        self.SetFont(wx.Font(13,wx.SWISS,wx.NORMAL,wx.BOLD))
        self.parent = parent
        # wx.Panel.SetBackgroundColour(self,(245,245,225))

        if hasattr(messenger,'__call__'):
            self.__messenger = messenger
        self.style = style
        self.format = "%.3f" 
        self.motor = None
        self.__sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.CreatePanel()

        self.SelectMotor(motor)

    @EpicsFunction
    def SelectMotor(self, motor):
        " set motor to a named motor PV"
        if motor is None:
            return

        if self.motor is not None:
            for i in self.__motor_fields:
                self.motor.clear_callback(attr=i)

        self.motor = epics.Motor(motor)
        self.motor.get_info()

        self.format = "%%.%if" % self.motor.precision
        self.FillPanel()

        self.set_Tweak(self.format % self.motor.tweak_val)
        for attr in self.__motor_fields:
            self.motor.get_pv(attr).add_callback(self.onMotorEvent,
                                                 wid=self.GetId(),
                                                 field=attr)

    @EpicsFunction
    def fillPanelComponents(self):
        if self.motor is None: return
        try:
            odr = self.motor.get_pv('drive')
            ord = self.motor.get_pv('readback') 
            ode = self.motor.get_pv('description')
        except:
            pass

        epics.poll()
        self.drive.set_pv(self.motor.get_pv('drive'))
        self.rbv.set_pv(self.motor.get_pv('readback') )

        descpv = self.motor.get_pv('description')
        if len(descpv.char_value) > 25:
            self.desc.Wrap(30)
            self.desc.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
            self.desc.SetSize( (200, 40))
        else:
            self.desc.Wrap(45)
            self.desc.SetFont(wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD))
            self.desc.SetSize( (200, -1))
            
        self.desc.set_pv(descpv)


        self.info.SetLabel('')
        for f in ('set', 'high_limit_set', 'low_limit_set',
                  'soft_limit', 'stop_go', 'enabled'):
            if self.motor.get_pv(f):
                uname = self.motor.get_pv(f).pvname
                wx.CallAfter(self.onMotorEvent,
                             pvname=uname, field=f)

            
    def CreatePanel(self,style='normal'):
        " build (but do not fill in) panel components"
        self.desc = pvText(self, size=(200, 25), 
                           font=wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD),
                           style=  wx.ALIGN_LEFT| wx.ST_NO_AUTORESIZE )
        self.desc.SetForegroundColour("Blue")

        self.rbv  = pvText(self, size=(105, 25),
                           fg='Blue',style=wx.ALIGN_CENTRE_VERTICAL|wx.ALIGN_RIGHT)
        self.info = wx.StaticText(self, label='', size=(90, 25), style=wx.ALIGN_CENTRE_VERTICAL|wx.ALIGN_RIGHT)
        self.info.SetForegroundColour("Red")

        self.drive = pvFloatCtrl(self,  size=(120,-1), style = wx.TE_RIGHT)
        
        self.fillPanelComponents()
                
        self.twk_list = ['','']
        self.__twkbox = wx.ComboBox(self, value='', size=(100,-1), 
                                    choices=self.twk_list,
                                    style=wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER)

        self.__twkbox.SetFont(wx.Font(13, wx.SWISS, wx.NORMAL, wx.BOLD))
        

        self.__twkbox.Bind(wx.EVT_COMBOBOX,    self.OnTweakBoxEvent)
        self.__twkbox.Bind(wx.EVT_TEXT_ENTER,  self.OnTweakBoxEvent)        

        twkbtn1 = wx.Button(self, label='<',  size=(30,30))
        twkbtn2 = wx.Button(self, label='>',  size=(30,30))
        stopbtn = wx.Button(self, label=' Stop ')
        morebtn = wx.Button(self, label=' More ')
        
        twkbtn1.Bind(wx.EVT_BUTTON, self.onLeftButton)
        twkbtn2.Bind(wx.EVT_BUTTON, self.onRightButton)
        stopbtn.Bind(wx.EVT_BUTTON, self.onStopButton)
        morebtn.Bind(wx.EVT_BUTTON, self.onMoreButton)

        self.stopbtn = stopbtn
        
        for b in (twkbtn1, twkbtn2):
            b.SetFont(wx.Font(12,wx.SWISS,wx.NORMAL,wx.BOLD,False))

        spacer = wx.StaticText(self, label=' ', size=(10, 10), style=wx.ALIGN_RIGHT)            
        self.__sizer.AddMany([(spacer,      0, wx.ALIGN_CENTER),
                              (self.desc,   0, wx.ALIGN_CENTRE_VERTICAL|wx.ALIGN_LEFT),
                              (self.info,   0, wx.ALIGN_CENTER),
                              (self.rbv,    0, wx.ALIGN_CENTER),
                              (self.drive,  0, wx.ALIGN_CENTER),
                              (twkbtn1,       0, wx.ALIGN_CENTER),
                              (self.__twkbox, 0, wx.ALIGN_CENTER),
                              (twkbtn2,       0, wx.ALIGN_CENTER),
                              (stopbtn,       0, wx.ALIGN_CENTER),
                              (morebtn,       0, wx.ALIGN_CENTER)
                              ] )

        self.SetAutoLayout(1)
        self.SetSizer(self.__sizer)
        self.__sizer.Fit(self)

    def FillPanel(self):
        " fill in panel components for motor "
        if self.motor is None: return

        self.fillPanelComponents()

        self.drive.update()
        self.desc.update()
        self.rbv.update()

        self.twk_list = self.Create_StepList()
        self.__Update_StepList()
        
    @EpicsFunction
    def onLeftButton(self,event=None):
        if (self.motor is None): return        
        self.motor.tweak(dir='reverse')
        
    @EpicsFunction
    def onRightButton(self,event=None):
        if (self.motor is None): return        
        self.motor.tweak(dir='forward')

    @EpicsFunction
    def onStopButton(self,event=None):
        curstate = str(self.stopbtn.GetLabel()).lower().strip()
        
        if self.motor is None:
            return
        self.motor.StopNow()
        epics.poll()
        val = 3
        if curstate == 'stop':   val = 0
        self.motor.put_field('stop_go', val)

    @EpicsFunction
    def onMoreButton(self,event=None):
        if (self.motor is None): return        
        x = MotorDetailFrame(parent=self, motor=self.motor)
            
    def OnTweakBoxEvent(self,event):
        if (self.motor is None): return
        try:
            self.motor.tweak_val = set_float(event.GetString())
        except:
            pass

    @DelayedEpicsCallback
    def onMotorEvent(self, pvname=None, field=None, event=None, **kw):
        if pvname is None: return None
      
        field_val = self.motor.get_field(field)
        field_str = self.motor.get_field(field, as_string=1)

        # print 'onMotor Event: ',  self.motor,  field, field_val, field_str
        sys.stdout.flush()
        
        if field == 'low_limit':
            self.drive.SetMin(self.motor.low_limit)
        elif field == 'high_limit':
            self.drive.SetMax(self.motor.high_limit)

        elif field in ('soft_limit', 'high_limit_set', 'low_limit_set'):
            s = 'Limit!'
            if (field_val == 0): s = ''
            self.info.SetLabel(s)
            
        elif field == 'set':
            label, color='Set:','Yellow'
            if field_val == 0:
                label,color='','White'
            self.info.SetLabel(label)
            self.drive.bgcol_valid = color
            self.drive.SetBackgroundColour(color)
            self.drive.Refresh()

        elif field == 'enabled':
            label = ('','Disabled')[field_val]
            self.info.SetLabel(label)
            
        elif field == 'tweak_val':
            self.set_Tweak(field_str)

        elif field == 'stop_go':
            label, info, color = 'Stop', '', 'White'
            if field_val == 0:
                label, info, color = ' Go ', 'Stopped', 'Yellow'
            elif field_val == 1:
                label, info, color = ' Resume ', 'Paused', 'Yellow'
            elif field_val == 2:
                label, info, color = ' Go ', 'Move Once', 'Yellow'
            self.stopbtn.SetLabel(label)
            self.info.SetLabel(info)
            self.stopbtn.SetBackgroundColour(color)
            self.stopbtn.Refresh()

        else:
            pass

    def set_Tweak(self,val):
        if not isinstance(val, str):
            val = self.format % val
        if val not in self.twk_list:  self.__Update_StepList(value=val)
        self.__twkbox.SetValue(val)
            
    def Create_StepList(self):
        """ create initial list of motor steps, based on motor range
        and precision"""


        if self.motor is None: return []
        smax = abs(self.motor.high_limit - self.motor.low_limit)*0.6

        p = self.motor.precision
        # print self.motor.high_limit, self.motor.low_limit, smax, p

        l = []
        for i in range(6):
            x = 10**(i-p)
            for j in (1,2,5):
                if (j*x < smax):  l.append(j*x)
        return [self.format%i for i in l]
    

    def __Update_StepList(self,value=None):
        "add a value and re-sort the list of Step values"
        if value is not None:
            self.twk_list.append(value)
        x = [float(i) for i in self.twk_list]
        x.sort()
        self.twk_list = [self.format % i for i in x]
        # remake list in TweakBox
        self.__twkbox.Clear()
        self.__twkbox.AppendItems(self.twk_list)
        
