#!/usr/bin/env python3
"""Draw the README housing illustration using the shared panel's coordinates."""
from pathlib import Path
from math import sin, cos, radians
from html import escape

ROOT = Path(__file__).resolve().parents[1]
out = []


def emit(markup):
    out.append(markup)


def rect(x, y, w, h, fill, radius=0, stroke=None, width=1):
    border = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ''
    emit(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"{border}/>')


def line(x, y, xx, yy, colour, width=1):
    emit(f'<path d="M{x:.2f} {y:.2f}L{xx:.2f} {yy:.2f}" stroke="{colour}" stroke-width="{width}"/>')


def circle(x, y, r, fill, stroke=None):
    border = f' stroke="{stroke}"' if stroke else ''
    emit(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"{border}/>')


def text(s, x, y, size=17, colour='#b7b7b5', weight=500, align='middle', spacing=0):
    emit(f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{align}" letter-spacing="{spacing}" fill="{colour}">{escape(s)}</text>')


def recess(x, y, w, h, radius=5):
    rect(x-3, y-3, w+6, h+6, '#080808', radius+2)
    rect(x, y+2, w, h, '#5c5c5a', radius)
    rect(x+1, y, w-2, h-2, '#090909', radius)


def button(x, y, w, h, label, active=False, size=13):
    rect(x-3, y, w+6, h+9, '#090909', 6)
    rect(x, y, w, h, 'url(#button)', 4, '#656562')
    rect(x+4, y+4, w-8, h-9, 'url(#buttonFace)', 3)
    line(x+7, y+4, x+w-7, y+4, '#858581')
    line(x+7, y+h-6, x+w-7, y+h-6, '#111111', 2)
    text(label, x+w/2, y+h*.58, size, '#dadad5', 700)
    rect(x+9, y+h-9, w-18, 2, '#b99a66' if active else '#676762', 1)


def knob(x, y, r, mark=0):
    for i in range(31):
        a=radians(-225+i*9)
        major=i%5==0
        line(x+cos(a)*(r+9), y+sin(a)*(r+9), x+cos(a)*(r+(18 if major else 13)), y+sin(a)*(r+(18 if major else 13)), '#9b9b94' if major else '#65655f', 2 if major else 1)
    circle(x, y+9, r+7, '#090909')
    circle(x, y+2, r+5, 'url(#collar)')
    circle(x, y, r+2, '#080808', '#72726c')
    points=[]
    for i in range(192):
        a=i*3.141592653589793/96
        rr=r-(1 if i%4<2 else 3)
        points.append(f'{x+cos(a)*rr:.2f},{y+sin(a)*rr:.2f}')
    emit(f'<polygon points="{" ".join(points)}" fill="url(#grip)" stroke="#080808" stroke-width="2"/>')
    for i in range(48):
        a=radians(i*7.5)
        line(x+cos(a)*(r-7),y+sin(a)*(r-7),x+cos(a)*(r-2),y+sin(a)*(r-2),'#686862' if sin(a)<0 else '#151515',1.2)
    circle(x,y,r-10,'url(#capRim)','#181818')
    circle(x,y,r-13,'url(#cap)','#484844')
    a=radians(-90+mark)
    line(x+cos(a)*(r-24),y+sin(a)*(r-24),x+cos(a)*(r-13),y+sin(a)*(r-13),'#deded6',4)


def sector(inner, outer, start, end, fill, stroke=None):
    points=[]
    for r, angles in [(outer, range(31)),(inner, range(30,-1,-1))]:
        for i in angles:
            a=radians(start+(end-start)*i/30)
            points.append(f'{1503+r*cos(a):.2f},{466+r*sin(a):.2f}')
    border=f' stroke="{stroke}" stroke-width="1.5"' if stroke else ''
    emit(f'<polygon points="{" ".join(points)}" fill="{fill}"{border}/>')


emit('''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="800" viewBox="0 0 1600 800" fill="none" role="img" aria-labelledby="title desc">
<title id="title">AFX-1000</title>
<desc id="desc">An angled view of the charcoal AFX-1000 housing, with a deep front lip, ribbed knobs, a circular Scene FX button bank, recessed X-Pad and release lever. Off-white panel lettering and small amber status lights.</desc>
<defs>
 <linearGradient id="background" x2="0" y2="1"><stop stop-color="#ededeb"/><stop offset="1" stop-color="#d5d5d1"/></linearGradient>
 <linearGradient id="body" x2="0" y2="1"><stop stop-color="#363635"/><stop offset=".55" stop-color="#161616"/><stop offset="1" stop-color="#080808"/></linearGradient>
 <linearGradient id="face" x2=".4" y2="1"><stop stop-color="#3b3b39"/><stop offset=".45" stop-color="#2b2b29"/><stop offset="1" stop-color="#222220"/></linearGradient>
 <linearGradient id="collar" x2="0" y2="1"><stop stop-color="#101010"/><stop offset="1" stop-color="#6b6b65"/></linearGradient>
 <linearGradient id="grip" x2=".3" y2="1"><stop stop-color="#686862"/><stop offset=".4" stop-color="#363633"/><stop offset="1" stop-color="#101010"/></linearGradient>
 <linearGradient id="capRim" x2="0" y2="1"><stop stop-color="#a2a298"/><stop offset=".25" stop-color="#686862"/><stop offset="1" stop-color="#20201e"/></linearGradient>
 <linearGradient id="cap" x2=".3" y2="1"><stop stop-color="#52524d"/><stop offset=".45" stop-color="#333330"/><stop offset="1" stop-color="#1c1c1a"/></linearGradient>
 <linearGradient id="button" x2="0" y2="1"><stop stop-color="#72726c"/><stop offset=".13" stop-color="#4b4b47"/><stop offset="1" stop-color="#222220"/></linearGradient>
 <linearGradient id="buttonFace" x2="0" y2="1"><stop stop-color="#50504b"/><stop offset="1" stop-color="#2b2b28"/></linearGradient>
 <linearGradient id="strip" x2="0" y2="1"><stop stop-color="#262624"/><stop offset=".3" stop-color="#141413"/><stop offset="1" stop-color="#090909"/></linearGradient>
 <linearGradient id="lever" x2="0" y2="1"><stop stop-color="#c9c9c0"/><stop offset=".15" stop-color="#95958c"/><stop offset=".75" stop-color="#575751"/><stop offset="1" stop-color="#31312d"/></linearGradient>
 <pattern id="finish" width="7" height="4" patternUnits="userSpaceOnUse"><path d="M0 .5H7" stroke="#fff" stroke-opacity=".018"/><path d="M2 2.5H6" stroke="#000" stroke-opacity=".04"/></pattern>
</defs>''')
rect(0,0,1600,800,'url(#background)',12)
# The ground shadow and visible front edge give the enclosure its thickness.
emit('<g transform="rotate(-2.2 828 657)">')
for i in range(22,0,-1):
    emit(f'<ellipse cx="828" cy="657" rx="{666+i*3}" ry="{20+i*1.6}" fill="#151513" opacity=".014"/>')
emit('</g>')
emit('<g transform="matrix(.66 -.025 .06 .62 94 88)">')
rect(1,23,2046,923,'#080808',30)
rect(1,17,2046,921,'url(#body)',30,'#151515',2)
line(40,929,2008,929,'#444440',2)
# Faceplate with a narrow machined seam and a separate moulded shell.
rect(0,0,2048,921,'#111111',28,'#595955',2)
rect(9,8,2030,900,'#52524e',22)
rect(14,13,2020,890,'#101010',19)
rect(23,23,2002,871,'url(#face)',13,'#74746d')
rect(24,24,2000,869,'url(#finish)',12)
line(40,26,2006,26,'#77776f')
line(40,893,2006,893,'#121212',2)
# Printing is intentionally small and belongs to the panel, not a surrounding ad.
text('AFX-1000',57,97,61,'#e0e0d7',800,'start',-2)
text('REMIX STATION',435,91,18,'#a3a39a',600,'start',1)
text('STEREO EFFECTS PROCESSOR',1980,78,12,'#98988f',500,'end',1)
line(44,275,1206,275,'#141414',3)
line(44,278,1206,278,'#565650')
line(1132,302,1132,856,'#121212',3)
line(1135,302,1135,856,'#565650')
# Input/output and clock section.
knob(112,180,42,-24); knob(690,180,42,15)
text('INPUT',112,122,16,'#cecec5',700)
text('OUTPUT',690,122,16,'#cecec5',700)
for y,label in [(133,'INPUT'),(217,'OUTPUT')]:
    text(label,235,y+16,12,'#b2b2a9',500,'end')
    recess(260,y,375,29)
    for i in range(27):
        rect(270+i*13.2,y+8,9,12,'#aaa589' if i<17 else '#2a2a25',1)
text('−∞      −24      −12       −6       0     +6',445,189,11,'#88887f')
button(768,114,120,47,'QUANTIZE',True,12)
text('NUDGE',829,200,12)
button(768,214,57,43,'−',False,23);button(832,214,57,43,'+',False,23)
text('BPM',984,127,19,'#cecec5',700)
recess(920,145,129,75)
text('128',984,202,48,'#c1b58d',500)
button(1097,114,88,47,'AUTO',True,13)
button(1103,197,77,63,'TAP',False,15)
# Isolator and sample area follow the real editor layout.
text('FX SOURCE',101,313,12)
text('ISOLATE FX',204,313,23,'#deded5',700,'start')
for x,label in [(394,'ISOLATOR'),(513,'CUT / ADD'),(747,'TRANS / ROLL'),(863,'GATE / DRIVE')]:
    button(x,339,88,43,label,label=='ISOLATOR',10)
button(54,339,90,48,'INPUT',True)
button(54,525,90,48,'X-PAD')
for x,label,mark in [(325,'LOW',-20),(668,'MID',0),(1019,'HI',12)]:
    knob(x,471,86,mark);text(label,x,588,20,'#d9d9cf',700)
recess(40,612,1053,247,7)
rect(44,616,1045,238,'#252523',5)
line(56,651,1077,651,'#4c4c46')
text('X-PAD FX',58,642,22,'#d0d0c6',700,'start')
button(198,664,52,50,'BANK',False,10)
button(342,664,89,50,'ROLL',False,12)
for i,label in enumerate(['KICK','SNARE','CLAP','HI-HAT']):
    x=458+i*115
    button(x,664,89,50,label,False,13)
    text(str(i+1),x+44.5,644,12,'#99998f')
button(993,664,54,50,'OVER',False,11)
text('DELETE',1020,733,10,'#93938a')
knob(118,792,40,-30);knob(330,792,47,0)
text('LEVEL',118,730,13,'#c0c0b7',600)
text('PITCH',330,730,13,'#c0c0b7',600)
recess(474,768,410,67)
rect(478,772,402,58,'url(#strip)',3)
for i in range(8):
    x=483+i*54
    line(x,778,x,791,'#939387')
    if i<7:line(x+27,778,x+27,785,'#5a5a52')
button(980,770,79,65,'HOLD',False,13)
text('MUTE',1020,852,10,'#93938a')
# Ten physical selector caps arranged around the Scene depth control.
text('SCENE FX',1503,115,26,'#deded4',700)
for i,label in enumerate(['BPF ECHO','ECHO','NOISE','SPIRAL UP','REVERB UP','HPF ECHO','LPF ECHO','CRUSH ECHO','SPIRAL DOWN','REVERB DOWN']):
    mid=-140.4+i*25.2 if i<5 else 140.4-(i-5)*25.2
    start,end=mid-12.1,mid+12.1
    sector(186,327,start-.5,end+.5,'#090909','#53534d')
    sector(192,322,start,end,'url(#button)','#71716a')
    sector(199,315,start+.55,end-.55,'url(#buttonFace)','#1c1c1a')
    sector(201,205,start+1.2,end-1.2,'#b79a69' if i==1 else '#727269')
    a=radians(mid)
    text(label,1503+cos(a)*258,471+sin(a)*258,12,'#d2d2c8',700)
knob(1503,466,78,32)
text('DEPTH',1503,584,15,'#c9c9bf',600)
for x,label,mark in [(1198,'SUB 1',-24),(1813,'SUB 2',20)]:
    knob(x,785,46,mark);text(label,x,715,14,'#c0c0b4',600)
text('TIME / SIZE',1198,866,12,'#9c9c91')
text('CHARACTER',1813,866,12,'#9c9c91')
text('SUB PARAMETER',1503,849,13,'#9c9c91',600)
# Release lever and small hardware selector.
text('DEFAULT / USER',1875,144,12,'#a8a89e')
button(1828,160,92,42,'DEFAULT',False,11)
text('RELEASE FX',1925,280,19,'#d2d2c8',700)
button(1890,313,85,47,'ECHO',False,13)
for i,label in enumerate(['BACK SPIN','ECHO','VINYL BRAKE']):
    text(label,1943,391+i*19,12,'#b0b0a6')
recess(1885,457,114,108,7)
rect(1895,474,94,32,'#000000',5)
rect(1891,465,102,30,'url(#lever)',5,'#8d8d82')
for i in range(3):line(1901,473+i*5,1983,473+i*5,'#4b4b45')
text('PULL / RELEASE',1942,588,10,'#94948a')
for x,y in [(35,35),(2013,35),(35,885),(2013,885)]:
    circle(x,y,8,'#111111','#62625b')
    circle(x,y,5,'#393934')
    line(x-2.5,y+2.5,x+2.5,y-2.5,'#080808',2)
emit('</g></svg>')
(ROOT/'assets/readme-hero.svg').write_text('\n'.join(out)+'\n')
