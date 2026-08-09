"""Measure the figure palette under simulated color-vision deficiency.

Converts each pair to sRGB, simulates the three dichromacies by the method of
Vienot, Brettel and Mollon (1999), and reports the CIE 1976 color difference
along with the grayscale luminance gap. A difference of about 2.3 is the
threshold at which two colors become noticeably different.

Reads nothing and writes nothing. The results are recorded in notes/study.md.
"""

from __future__ import annotations

import numpy as np
def hex2rgb(h): return np.array([int(h[i:i+2],16)/255 for i in (1,3,5)])
def srgb2lin(c): return np.where(c<=0.04045, c/12.92, ((np.clip(c,0,1)+0.055)/1.055)**2.4)
def lin2srgb(c):
    c=np.clip(c,0,1); return np.where(c<=0.0031308, c*12.92, 1.055*c**(1/2.4)-0.055)
M=np.array([[17.8824,43.5161,4.11935],[3.45565,27.1554,3.86714],[0.0299566,0.184309,1.46709]]); Mi=np.linalg.inv(M)
SIM={'deuteranopia':np.array([[1,0,0],[0.494207,0,1.24827],[0,0,1]]),
     'protanopia':np.array([[0,2.02344,-2.52581],[0,1,0],[0,0,1]]),
     'tritanopia':np.array([[1,0,0],[0,1,0],[-0.395913,0.801109,0]])}
def sim(rgb,k): return lin2srgb(Mi@(SIM[k]@(M@srgb2lin(rgb))))
def lab(rgb):
    lin=srgb2lin(rgb); X=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
    xyz=(X@lin)/np.array([0.95047,1.0,1.08883]); f=np.where(xyz>0.008856,np.cbrt(xyz),7.787*xyz+16/116)
    return np.array([116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])])
def dE(a,b): return float(np.linalg.norm(lab(a)-lab(b)))
def luma(rgb): return float(np.dot(srgb2lin(rgb),[0.2126,0.7152,0.0722]))

def report(name, pairs):
    print(f'\n=== {name} ===')
    print(f"{'pair':40s} {'normal':>7s} {'deut':>7s} {'prot':>7s} {'trit':>7s} {'min CVD':>8s} {'grayDL':>7s}")
    worst=1e9
    for la,a,lb,b in pairs:
        ra,rb=hex2rgb(a),hex2rgb(b)
        vals=[dE(ra,rb)]+[dE(sim(ra,k),sim(rb,k)) for k in ('deuteranopia','protanopia','tritanopia')]
        mn=min(vals[1:]); worst=min(worst,mn)
        print(f'{la+" vs "+lb:40s} '+' '.join(f'{v:7.1f}' for v in vals)+f' {mn:8.1f} {abs(luma(ra)-luma(rb)):7.3f}')
    print(f'  worst-case minimum across all pairs: {worst:.1f}')
    return worst

report('SUPPORT STATUS (as specified)', [('inside','#0072B2','outside','#D55E00')])
a=report('VARIANTS as specified (clamped reuses the support blue)',
    [('clamped','#0072B2','unclamped','#CC79A7'),('clamped','#0072B2','reduced','#7F7F7F'),
     ('unclamped','#CC79A7','reduced','#7F7F7F')])
b=report('VARIANTS, proposed: bluish-green / reddish-purple / gray',
    [('clamped','#009E73','unclamped','#CC79A7'),('clamped','#009E73','reduced','#7F7F7F'),
     ('unclamped','#CC79A7','reduced','#7F7F7F')])
c=report('VARIANTS, achromatic alternative',
    [('clamped','#1A1A1A','unclamped','#767676'),('clamped','#1A1A1A','reduced','#B0B0B0'),
     ('unclamped','#767676','reduced','#B0B0B0')])
print('\ncross-check: do the proposed variant hues collide with the support hues?')
for ln,c1 in [('support inside','#0072B2'),('support outside','#D55E00')]:
    for vn,c2 in [('clamped','#009E73'),('unclamped','#CC79A7'),('reduced','#7F7F7F')]:
        vals=[dE(sim(hex2rgb(c1),k),sim(hex2rgb(c2),k)) for k in SIM]
        print(f'  {ln:16s} vs {vn:10s} min CVD dE = {min(vals):6.1f}')
