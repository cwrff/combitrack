# Variant of combitrack.py : build a GPX library with combined roundtrips
#    issued from an OSM network
# Bernard HOUSSAIS - FF Randonnée 35 - bh35@orange.fr
# Release 2.5 - Feb 2025

Slices = [5, 9, 12, 15, 20, 25, 30] # 5-9 km, 9-12 km, etc.
Nb_tracks = [3, 5, 4, 5, 4, 4] # Max number of tracks for each slice
QualMin = 5.0  # Min quality for selected tracks

import sys
from tkinter import *
from tkinter import ttk
import xml.sax as sax
from math import sqrt, cos
deb = 0 # 0 .. 3 : level of debug prints
Start_nodes_output = True  # output as waypoints in network GPX file

print("\nCOMBI BASE - Feb 2025\n")

# proposed quality (/10) for elementary OSM ways
mark = {}
mark["unclassified"] = 2
mark["residential"] = 3
mark["service"] = 3
mark["living_street"] = 4
mark["pedestrian"] = 6
mark["track"] = 6  # may be modified according to tracktype
mark["steps"] = 6
mark["footway"] = 9
mark["bridleway"] = 9
mark["cycleway"] = 7
mark["path"] = 10
# mark[others] = 0

mark_tracktype = [4, 5, 7, 8, 9]
    # grade1 -> quality = 4, grade2 = 5, g3 = 7, g4 = 8, g5 = 9

Nb_Slices = len(Nb_tracks)
it = 1
while it < len(Slices) and Slices[it] > Slices[it-1]:
    it += 1
if len(Slices) != Nb_Slices+1 or it < len(Slices):
    print("Slices definition erroneous !")
    sys.exit()

# window for input parameters
root = Tk(className='Combi base')
mwin = ttk.Frame(root)  # main window
mwin.grid(column=0, row=0)
messNw = ttk.Label(mwin,text="Network :")
messNw.grid(column=0, row=0)

try:
    fmem = open('.memb.txt','r')
    prevNw = fmem.readline()[:-1]  # string without newline
    prevSt = fmem.readline()[:-1]
    prevGn = fmem.readline()[:-1]
    fmem.close()
except:
    try:
        fother = open('.memo.txt','r')
        prevNw = fother.readline()[:-1]
        prevSt = prevGn = ''
        fother.close()
    except:
        prevNw = prevSt = prevGn = ''

varNw = StringVar(mwin,prevNw)
entNw = ttk.Entry(mwin,textvariable=varNw,width=60)
entNw.grid(column=1,row=0,columnspan=4)

messSt = ttk.Label(mwin,text="  Start :\n(empty = analysis only)")
messSt.grid(column=0, row=1)
varSt = StringVar(mwin,prevSt)
entSt = ttk.Entry(mwin,textvariable=varSt,width=60)
entSt.grid(column=1,row=1,columnspan=4)

messGn = ttk.Label(mwin,text="Name of GPX files:\n(empty = Start)")
messGn.grid(column=0, row=2)
varGn = StringVar(mwin,prevGn)
entGn = ttk.Entry(mwin,textvariable=varGn,width=60)
entGn.grid(column=1,row=2,columnspan=4)

gow = ttk.Button(mwin,text="Go !",command=root.destroy)
gow.grid(column=1,row=3)

root.mainloop()

inputOSMFile = varNw.get()
if inputOSMFile == "":  # empty network file name = Cancel button
    sys.exit()
startName = varSt.get()
SolName = varGn.get()
if inputOSMFile[-4:] != '.osm':
    inputOSMFile += '.osm'
print ("OSM network : ", inputOSMFile);
rootName = inputOSMFile[:-4]
fullName = inputOSMFile

fmem = open('.memb.txt','w')
fmem.write(fullName+'\n'+startName+'\n'+SolName+'\n')
fmem.close()

# "Net.osm" may be in working_directory
#   or in a sub-directory : "Net/Net.osm" or "SomeDir/Net.osm"

j=rootName.find('/')
if j < 0:  # current directory
  try:
    osmFile = open(inputOSMFile,"r")
  except:
    try:  # sub-directory with same name
        osmFile = open(rootName+'/'+inputOSMFile,"r")
        rootName = rootName+'/'+rootName
        inputOSMFile = rootName+'.osm'
    except:
        print("\nFile",inputOSMFile,"can't be opened")
        sys.exit()
else:  # sub-directory with given name (before "/")
    try:
        osmFile = open(inputOSMFile,"r")
    except:
        print("\nFile",inputOSMFile,"can't be opened")
        sys.exit()

if rootName.find('/') < 0:
    netGPXFile = "_"+rootName+".gpx"  # input network displayed in GPX format
else:
    netGPXFile = rootName.replace('/','/_')+".gpx"

startNode = None
lgMin = Slices[0]
lgMax = Slices[-1]
maxBest = 99999  # not limited

def norm_string (s1): # s1 : string to normalize
    s2 = ""
    i1 = 0
    while i1 < len(s1) and (s1[i1] < 'A' or s1[i1] > 'z'):
        i1 += 1
    while i1 < len(s1):
        c1 = s1[i1]
        #if c1>='A' and c1<='Z':
        #    c1 = chr(ord(c1)+32)
        if c1=='é' or c1=='è' or c1=='ê' or c1=='ë' or c1=='É':
            c1 = 'e'
        elif c1=='à' or c1=='â':
            c1 = 'a'
        elif c1=='ô':
            c1 = 'o'
        elif c1=='ù' or c1=='û':
            c1 = 'u'
        elif c1=='ç':
            c1 = 'c'
        elif c1 == ' ' or c1<'0' or c1>'9' and c1<'A' or c1>'Z' and c1<'a' or c1>'z':
            c1 = '-'
        if c1 == 't' and i1 >= 4 and (s2[-4:]=='sain' or s2[-4:]=='Sain'):
            s2 = s2[:-3]+'t'     # saint => st
        elif c1 != ' ':
            s2 = s2+c1
        i1 = i1+1
    # print("Norm :", s2)
    return s2

normSN = norm_string(startName)
lgSN = len(normSN)

class DictHandler(sax.handler.ContentHandler):

    def __init__(self): 
        self.inWay = False
        self.inNode = False
        
    def setDb(self, db):
        self.db = db


    def startElement(self, name, attrs): 
        # new element in osm file

        if name == "node":
            idn = attrs["id"]
            slat = attrs["lat"]
            slon = attrs["lon"]
            self.inNode = True
            if idn in self.db.nodesDict: # already ref in <nd ref = .../>
                self.newNode = self.db.nodesDict[idn]
                self.newNode.slat = slat   # latitude as a string
                self.newNode.lat = eval(slat)
                self.newNode.slon = slon
                self.newNode.lon = eval(slon)
            else:  # new node definition
                refNd = ""
                ll = slat+slon
                if ll in self.db.laloDict: # node already seen with other ident
                    refNd = self.db.laloDict[ll].refNd
                else:
                    self.db.laloDict[ll] = lalo(idn)
                self.newNode = node(idn,refNd,slat,slon)

        elif name == "way":
            #print ("Way : ", attrs["id"])
            self.inWay = True
            self.newWay = way()
            self.newWay.iBegin = len(self.db.wayNodes)
            # Nodes of the way between iBegin and iEnd in wayNodes

        elif name == "nd":
            idn = attrs["ref"]
            if not(idn in self.db.nodesDict): # first occur
                nd = node(idn,idn,"0.0","0.0")
                self.db.nodesDict[idn] = nd
            else:              # node already seen
                nd = self.db.nodesDict[idn]
                if nd.refNd != "":
                    nd = self.db.nodesDict[nd.refNd]
            if self.inWay:
                self.db.wayNodes.append(nd)

        elif name == "tag":
            k = attrs["k"]
            if self.inWay:
                if k == "highway":
                    kind = attrs["v"]
                    if kind in mark:
                        self.newWay.qual = mark[kind] # 0 otherwise
                elif k == "tracktype":
                    grade = eval(attrs["v"][5])
                    if grade > 0 and grade <=5:
                        self.newWay.qual = mark_tracktype[grade-1]
                elif k=="name" or (k=="ref" and self.newWay.name == ""):
                    self.newWay.name = attrs["v"]
                elif k=="return" or k=="aller-retour":
                    if attrs["v"] == "yes":
                        self.newWay.Ret = 1
                    else:
                        self.newWay.Ret = 0
            elif self.inNode:
                if k=="combi" or k=="start" or k=="depart":
                    self.newNode.name = attrs["v"]
                    if self.newNode.refNd != "":
                        db.nodesDict[self.newNode.refNd].name = attrs["v"]
                        # name copied to first seen node

    def endElement(self, name): 
      global startNode,lgSN
      if self.inWay and name == "way":              
        self.newWay.iEnd = len(self.db.wayNodes)-1
        lgW1 = self.newWay.iEnd - self.newWay.iBegin
        if lgW1 > 0: # way not empty
          # way already seen ?
          ndB = self.db.wayNodes[self.newWay.iBegin]
          ndE = self.db.wayNodes[self.newWay.iEnd]
          iw = len(self.db.listWay)
          nfoundW = True
          while nfoundW and iw > 0:
            iw = iw-1
            w = self.db.listWay[iw]
            if w.iEnd-w.iBegin == lgW1:
              iNd = lgW1
              if self.db.wayNodes[w.iBegin] == ndB:
                while iNd > 0 and self.db.wayNodes[w.iBegin+iNd] == self.db.wayNodes[self.newWay.iBegin+iNd]:
                  iNd = iNd-1
              elif self.db.wayNodes[w.iBegin] == ndE:
                while iNd > 0 and self.db.wayNodes[w.iBegin+iNd] == self.db.wayNodes[self.newWay.iEnd-iNd]:
                  iNd = iNd-1
              nfoundW = iNd > 0
          if nfoundW:  # new way
              iNd = self.newWay.iBegin
              while iNd < self.newWay.iEnd:
                 ndB.nbArc = ndB.nbArc+1
                 iNd = iNd+1
                 ndB = self.db.wayNodes[iNd]
              ndE.nbArc = ndE.nbArc+1
              self.db.listWay.append(self.newWay)
        self.inWay=False
    
      elif self.inNode and name == "node":
          if self.newNode.name != "":  # start node
              nnm = norm_string(self.newNode.name)
              if lgSN > 0 and normSN == nnm[:lgSN]:
                  startNode = self.newNode
              self.newNode.nbArc = 99  # node treated as a connection
          self.db.nodesDict[self.newNode.idn] = self.newNode
          self.inNode = False

class way():
  def __init__(self):
      self.iBegin = -1  # index of the first node in wayNodes
      self.iEnd = -1
      self.qual = 0.0   # First : quality, then quality * length
      self.length = 0.0
      self.Ret = 0  # 1 : Return allowed
      self.name = ""

class merged(): # merging simple ways between connections
  def __init__(self,nbm,nd1,nd2,length,qual,Ret):
      self.nbm = nbm  # ident number of current merged way
      self.nd1 = nd1  # nodes on extremities
      self.nd2 = nd2
      self.n_ord1 = 0 # order of way from nd1
      self.n_ord2 = 0 # order of way from nd2
      self.length = length
      self.qual = qual  # quality * length
      self.state = Ret  # 0/1 : free / 4 : used
           # 2 : Return way used from nd1 to nd2 // 3 : from nd2 to nd1

class wmElem():
  # elem in list of ways
  def __init__(self,w,nxt):
      self.w = w    # simple way
      self.m = None # merged way
      self.next = nxt # other wmElem starting from same node

class node():
  def __init__(self,idn,refNd,slat,slon):
    self.idn = idn
    self.refNd = refNd  # not empty string : other ident for same node
    self.nbArc = 0 # number of ways starting from node (to detect connections)
    self.headWM = None  # head of list of ways beginning or ending with the node
    self.ist = -1  # when node in a track, index of node in the stack
    self.slat = slat
    self.lat = eval(slat)
    self.slon = slon
    self.lon = eval(slon)
    self.dist2Final = 999.0
    self.name = ""

class lalo():
    def __init__(self,refNd):
        self.refNd = refNd

class QLS():   # solution track (quality, length, stack of ways)
    def __init__(self,Q,L,S):
        self.q = Q
        self.l = L
        T = 0
        while T < Nb_Slices-1 and L > Slices[T+1]:
            T += 1
        self.t = T        
        self.s = S

def beforeSol(s1,s2): # relation d'ordre entre solutions
    if s1.t == s2.t:
        return s1.q > s2.q
    else:
        return s1.t < s2.t

def fdiv(adsol):  # calcul de la diversité entre les solutions en 1 et en adsol
    if HSol[1].l > HSol[adsol].l:
        st1 = HSol[1].s
        L = HSol[1].l
        st2 = HSol[adsol].s
    else:
        st1 = HSol[adsol].s
        L = HSol[adsol].l
        st2 = HSol[1].s
    L1 = len(st1)
    L2 = len(st2)
    js = 0     # st1 et st2 ont souvent un début commun
    while js < min(L1,L2) and st1[js] == st2[js]:
        js += 1
    Ldif = 0.0
    for i in range(js,L1):
        j = js
        while j < L2 and st1[i] != st2[j]:
            j += 1
        if j >= L2: # élément de st1 absent de st2
            Ldif += st1[i].m.length
    return 10.0*Ldif/L
    
class objc():  # objet susceptible d'être conservé
    def __init__(self,adoc):
        self.adoc = adoc   # adresse dans le heaptree
        self.td = []   # liste des diversités vs objets précédents
        self.Dmin = 20.0 # Diversité minimum dans la tranche
        self.Imin = 0

class initDb():
    def __init__(self):
        self.nodesDict = {}  # dictionary
        self.laloDict = {}
        self.wayNodes = []
        self.listWay = []
         
def readDb(osmFile,db): 
    handler = DictHandler() 
    handler.setDb(db)
    parser = sax.make_parser() 
    parser.setContentHandler(handler)
    parser.parse(osmFile)

def initGPX(gf):
    gf.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    gf.write('<gpx version="1.1"\n')
    gf.write('creator="Combi base - Bernard Houssais"\n')
    gf.write('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
    gf.write('xmlns="http://www.topografix.com/GPX/1/1"\n')
    gf.write('xsi:schemaLocation="http://www.topografix.com/GPX/1/1\n')
    gf.write('http://www.topografix.com/GPX/1/1/gpx.xsd">\n')

def outNode(gf,nd):
    gf.write(' <trkpt lat="')
    gf.write(nd.slat)
    gf.write('" lon="')
    gf.write(nd.slon)
    gf.write('"></trkpt>\n')

def outWay(gf,w,firstNd): # first node already output
    if db.wayNodes[w.iBegin] == firstNd: # forward
        for i in range(w.iBegin,w.iEnd):
            nd = db.wayNodes[i+1]
            if gf != None:
                outNode(gf,nd)
    else:    # backward
        for i in reversed(range(w.iBegin,w.iEnd)):
            nd = db.wayNodes[i]
            if gf != None:
                outNode(gf,nd)
    return nd    # last node

def outSol(gf,nomSol,sol):
    gf.write('<trk> <name> '+nomSol+' </name>\n')
    gf.write('<trkseg>\n')
    nd = startNode
    outNode(gf,startNode)
    for wm in sol:
        w = wm.w
        Go = True
        while Go:
            nd = outWay(gf,w,nd)
            if nd.nbArc > 2:
                Go = False
            else:
                wm = nd.headWM
                if wm.w != w or nd.nbArc == 1:
                    w = wm.w
                else:
                    w = wm.next.w
    gf.write('</trkseg> </trk>\n')

# MAIN PROGRAM
# build Data Base
lu = osmFile.read(1) # maybe UTF-8 BOM characters beginning osm file
while lu != '>':
    lu = osmFile.read(1)
db = initDb()
readDb(osmFile,db)
osmFile.close()

if startName == "":
    maxBest = 0
if maxBest > 0:
    if startNode == None:
        print('\nBEWARE : unknown start node "'+startName+'"\n')
        maxBest = 0
    else:
        if startNode.refNd != "":
            startNode = db.nodesDict[startNode.refNd]
        startNode.nbArc = 99 # treated as a connection
        
parse = maxBest <= 0  # Only network analysis wanted
if parse:
    print("\nNETWORK ANALYSIS")
mGPXFile = open(netGPXFile,'w')
initGPX(mGPXFile)

coefLat = 111.29 # length in km of 1 degree in lat
someLat = db.wayNodes[0].lat
coefLon = 111.29 * cos(0.0174533*someLat) # same in lon, 0.017 = pi/180

# slicing of ways betwen connections
indWay = len(db.listWay)-1
while indWay >= 0:      # decreasing loop on ways, w = current Way
    w = db.listWay[indWay]
    nd = db.wayNodes[w.iEnd]
    ndEnd = nd
    # print("indWay  ",indWay,w.name,db.wayNodes[w.iBegin].idn,nd.idn,nd.nbArc)
    prevLat = nd.lat
    prevLon = nd.lon
    lg = 0.0
    # decreasing loop on nodes of the Way, except first and last nodes
    indNode = w.iEnd-1
    while indNode > w.iBegin:
        nd = db.wayNodes[indNode]
        lg = lg+sqrt((coefLat*(nd.lat-prevLat))**2+(coefLon*(nd.lon-prevLon))**2)
        prevLat = nd.lat
        prevLon = nd.lon
        if nd.nbArc > 1:
            # node is a connection
            nd.nbArc = nd.nbArc+1 # split way in nd
            newWay = way()      # create a new slice at the end of listWay
            newWay.iBegin = indNode
            newWay.iEnd = w.iEnd  # modified
            newWay.qual = w.qual*lg
            newWay.length = lg
            newWay.Ret = w.Ret
            newWay.name = w.name
            db.listWay.append(newWay)
            lg = 0.0
            # indNode : first of new way, and last of previous
            w.iEnd = indNode
            ndEnd = nd
            # print("I-slice ",db.wayNodes[newWay.iBegin].idn," -> ",db.wayNodes[newWay.iEnd].idn,newWay.name,newWay.length)
        indNode = indNode-1
    nd = db.wayNodes[w.iBegin]
    w.length = lg+sqrt((coefLat*(nd.lat-prevLat))**2+(coefLon*(nd.lon-prevLon))**2)
    w.qual = w.qual * w.length
    # print("M-slice ",nd.idn," -> ",ndEnd.idn,db.listWay[indWay].name,w.length)
    indWay =indWay-1
nbw = len(db.listWay)
# print(nbw,"ways after slicing")

# removing dead-ends
caseDe = 0  # 1 : dead-end found, -1 : not found, 0 : first look
while caseDe >= 0:
    caseDe = -caseDe
    # if some ways removed, all ways must be re-examined
    for iw in range(nbw):
        w = db.listWay[iw]
        if w != None:
            ndB = db.wayNodes[w.iBegin]
            ndE = db.wayNodes[w.iEnd]
            if (ndB.nbArc<=1 or ndE.nbArc<=1) and w.Ret == 0: # dead-end
                if caseDe == 0:
                    print("\n BEWARE : dead-ends removed !")
                    if parse:  # network analysis => output
                        print(" Look waypoint(s) XX on",netGPXFile,"\n")
                if ndB.nbArc <= 1:
                    if parse and ndB.nbArc == 1:
                        print("  ("+ndB.slat+","+ndB.slon+")")
                        mGPXFile.write('<wpt lat="'+ndB.slat+'" lon="'+ndB.slon+'"><name>XX</name></wpt>\n')
                    if ndE.nbArc == 2:
                        ndE.nbArc = 1
                else:
                    if parse and ndE.nbArc == 1:
                        print("  ("+ndE.slat+","+ndE.slon+")")
                        mGPXFile.write('<wpt lat="'+ndE.slat+'" lon="'+ndE.slon+'"><name>XX</name></wpt>\n')
                    if ndB.nbArc == 2:
                        ndB.nbArc = 1
                ndB.nbArc = ndB.nbArc-1
                ndE.nbArc = ndE.nbArc-1
                db.listWay[iw] = None  # way removed
                caseDe = 1
    # end loop on ways
    if caseDe == 0:
        caseDe = -1
# end while
# print(nbw,"ways not dead-end")

# list of ways starting from each connection
nbw = 0
for w in db.listWay:
    if w != None:
        nbw = nbw+1
        nd = db.wayNodes[w.iBegin]
        nd.headWM = wmElem(w,nd.headWM) # add in head of list
        nn = db.wayNodes[w.iEnd]
        if nn != nd:
            nn.headWM = wmElem(w,nn.headWM) # add in head of list
# if only one way from startNode, it may be used in Return mode
if not parse and startNode.headWM.next == None:
        startNode.headWM.w.Ret = 1

if parse:
    print("\nPossible Start points :")
    nameList = {}
trackName = ""  # root of network tracks name
i=0
while len(trackName) < 5:
    if i>=len(rootName):
        c = '-'
    else:
        c = rootName[i]
        if c == 't' and len(trackName) == 4 and trackName[:4] == 'Sain':
            trackName = 'S'
        elif c<'A' or c>'Z' and c<'a' or c>'z':
            c = '-'
    trackName = trackName + c
    i += 1

# merging of ways between connections
nbm = 0
for idn in db.nodesDict:
    nd = db.nodesDict[idn]
    if nd.name != "":
        if Start_nodes_output:
            mGPXFile.write('<wpt lat="'+nd.slat+'" lon="'+nd.slon+'">\n')
            mGPXFile.write('    <name>'+nd.name+'</name> </wpt>\n')
        if parse and not (nd.name in nameList):
            print(nd.name)
            nameList[nd.name] = 0
    if nd.nbArc > 2: # connection
        if startNode != None:
          nd.dist2Final=lgMax-sqrt((coefLat*(nd.lat-startNode.lat))**2+(coefLon*(nd.lon-startNode.lon))**2)
        wm = nd.headWM
        pwmRet1 = None
        while wm != None: # loop on ways starting from nd
            if wm.m == None:  # not yet merged
                w = wm.w    # first way of merged way
                # Return allowed for merged way if allowed for some member
                prev_node = nd
                prevWM = wm
                ret = w.Ret
                simple_way = True
                while ret == 0 and simple_way:
                    nn = db.wayNodes[prevWM.w.iEnd]
                    if nn == prev_node:
                        nn = db.wayNodes[prevWM.w.iBegin]
                    # nn = last node of w = first node of next way
                    prev_node = nn
                    if nn.nbArc > 2:
                        simple_way = False
                    else:   # 2 ways from nn
                        nextWM = nn.headWM
                        if nextWM.w == prevWM.w:
                            nextWM = nextWM.next
                        prevWM = nextWM
                        ret = prevWM.w.Ret
                # set "Return status" of merged way
                
                if ret == 1: # Return allowed : special name and colour
                    nTrk = trackName+str(1001+nbm)[1:]
                    colour = "ff0000" # red
                else:
                    nTrk = trackName+str(999-nbm)
                    colour = "000080" # dark purple
                mGPXFile.write('<trk><name>'+nTrk+'</name>\n')
                mGPXFile.write('<extensions><line\n')
                mGPXFile.write('xmlns="http://www.topografix.com/GPX/gpx_style/0/2">\n')
                mGPXFile.write('<color>'+colour+'</color></line></extensions>\n')
                mGPXFile.write('<trkseg>\n')
                outNode(mGPXFile,nd)
                nn = outWay(mGPXFile,w,nd)
                # nn already output
                lg = w.length
                ql = w.qual
                prevWM = wm
                while nn.nbArc <= 2:  # following simple ways
                    nextWM = nn.headWM  # next way among only 2 ways
                    if nn.nbArc == 2 and nextWM.w == prevWM.w:
                        nextWM = nextWM.next # the other one
                    # nbArc == 1 when return track from a POI
                    #   Merged way will contain forward then backward tracks
                    w = nextWM.w
                    nn = outWay(mGPXFile,w,nn)
                    lg = lg + w.length
                    ql = ql + w.qual
                    prevWM = nextWM
                if nn.nbArc > 2:  # connection, end merged way
                    nbm = nbm+1
                    wm.m = merged(nbm,nd,nn,lg,ql,ret)
                    if nn == nd: # merged way is a simple loop
                        wm.m.state = 0  # no return
                    else:
                        pwmRet2 = None
                        # connect other end of merged way (node nn)
                        lastWM = nn.headWM # loop on ways starting from nn
                        while lastWM.w != prevWM.w:
                            pwmRet2 = lastWM
                            lastWM = lastWM.next
                        lastWM.m = wm.m
                    mGPXFile.write('</trkseg> </trk>\n')

                    # Warning about nearly identical ways
                    if parse and nn != nd:
                        im = nd.headWM
                        while im != wm:
                          if im.m.nd2 == nn and abs(im.m.length-lg)/lg < 0.02:
                            print("\n     BEWARE : tracks with same length, maybe duplicate ?")
                            print("     Between waypoints YY - ZZ on",netGPXFile)
                            mGPXFile.write('<wpt lat="'+nd.slat+'" lon="'+nd.slon+'"><name>YY</name></wpt>\n')
                            mGPXFile.write('<wpt lat="'+nn.slat+'" lon="'+nn.slon+'"><name>ZZ</name></wpt>\n')
                            print("     Difference in lengths : {:.1f}%\n".format(100*abs(im.m.length-lg)/lg))
                          im = im.next

                    # put Return ways before others
                    if ret == 1:
                        if pwmRet1 != None:  # wm not already first
                            pwmRet1.next = wm.next
                            wm.next = nd.headWM
                            nd.headWM = wm
                            wm = pwmRet1
                        if pwmRet2 != None: # same from other end
                            pwmRet2.next = lastWM.next
                            lastWM.next = nn.headWM
                            nn.headWM = lastWM
            # end if new merged way
            pwmRet1 = wm
            wm = wm.next
        # end list of ways from nd

        # set order of ways from nd
        wm = nd.headWM
        n_ord = 0
        while wm != None:
            n_ord += 1
            if nd == wm.m.nd1:
                wm.m.n_ord1 = n_ord
            if nd == wm.m.nd2:  # simple loop : same n_ord
                wm.m.n_ord2 = n_ord
            wm = wm.next
    # end case nd connection
# end loop on nodes
mGPXFile.write('</gpx>\n')
mGPXFile.close()
print('\n', nbm, "branches. Network in GPX format on ",netGPXFile,'\n')

if not parse:
  norm_Start_name = norm_string(startNode.name)
  fmem = open('.memb.txt','w')
  fmem.write(fullName+'\n')
  fmem.write(norm_Start_name+'\n')
  SolName = norm_string(SolName)
  fmem.write(SolName+'\n')
  fmem.close()
  if len(SolName) == 0:
      SolName = norm_Start_name # not memorized when equal StartName
  outputList = 'A_'+SolName+'.txt'
  listFile = open(outputList,'w')
  listFile.write('Network : '+inputOSMFile+'\n')
  print('Start :',norm_Start_name)
  listFile.write('Start : '+norm_Start_name+'\n')
  print('GPX files : '+SolName+'_....km.gpx')

                #   MAIN LOOP 
  nSol = 0  # number of computed solutions
  nBest = 0  # number of stored solutions
  HSol = [QLS(99.0,0.0,None)]  # tracks are stored in a heap tree
                              # heap tree is an array [1:...]
  
  totL = 0.0  # for current solution
  totQL = 0.0
  minL = 999.0
  maxL = 0.0

  nd = startNode
  wm = nd.headWM
  stack = []   # for ways wm
  st_bis = []  # (node nd, order of wm, ist, state, length, qual)

Go = not parse and lgMax > 0.0
while Go:
    if wm != None:
        m = wm.m
        direct = nd == m.nd1  # merged way from nd1 to nd2
        if direct:
            n_ord = m.n_ord1
            n_orde = m.n_ord2  # end of the way
            otherNd = m.nd2
        else:
            n_ord = m.n_ord2
            n_orde = m.n_ord1
            otherNd = m.nd1
        # print('M',m.nbm, '-', n_ord, '>', n_orde, m.state,direct)
        okWay = m.state < 4 # roundtrip only
        if okWay and m.state > 0 and len(stack) > 0: # Return track
            okWay = m.nbm!=stack[-1].m.nbm and (m.state==1 or (direct and m.state==3) or (not direct and m.state==2))
                    # not immediate return, and use free direction
        if okWay:
            okWay = totL + m.length <= otherNd.dist2Final
                # not too far from final node

        if okWay:   # loops management
            istp = otherNd.ist  # last index in the stack of other node
            okWay = istp < 0  # True : not in the stack
            if not okWay: # track makes a loop on otherNd
                (xnd,n_ordp,istpp,xstate,xlg,xql) = st_bis[istp]
                okWay = n_orde >= n_ordp
                # False means loop previously run in reverse sense
                if okWay and istpp >= 0:  # possible previous loop 
                    (xnd,n_ordpp,xist,xstate,xlg,xql) = st_bis[istpp]
                    okWay = n_ordp > n_ordpp  # never = : same node
                    if deb >= 2:
                        print('MLoop',istp,istpp,n_ordp,n_ordpp)
                        t=[]  # print ways of the stack
                        for ws in stack:
                            t.append(ws.m.nbm)
                        print(t,'\n')                        
            # False : in multi-loop case, current loop out of order, already run

        if not okWay:
            wm = wm.next

        else:  # way accepted
            if otherNd == startNode:
                SolL = totL + m.length
                totQ = (totQL+m.qual)/SolL
                if SolL >= lgMin and totQ >= QualMin:   # Solution found
                    nSol = nSol+1                    
                    if nSol % 10000 == 0:
                        print(nSol,"solutions now")
                    if SolL < minL:
                        minL = SolL
                        minQ = totQ
                    if SolL > maxL:
                        maxL = SolL
                        maxQ = totQ
                    stSol = stack[:]
                    stSol.append(wm)
                    NewSol = QLS(totQ,SolL,stSol)
                    if deb >= 1:
                        print("SOL",nSol,'L={:.2f} Q={:.2f}'.format(SolL,totQ))
                        t=[]  # print ways of the solution
                        for ws in stSol:
                            t.append(ws.m.nbm)
                        print(t,'\n')                        
                    # Store the solution in the heap tree
                    # Higher quality at the root (index 1)
                    HSol.append(None)
                    freep = nSol   # free place
                    fp2 = freep//2
                    while freep > 1 and beforeSol(NewSol,HSol[fp2]):
                        HSol[freep] = HSol[fp2]
                        freep = fp2
                        fp2 = freep//2
                    HSol[freep] = NewSol
              # end solution management, next choice

                if deb >= 2:
                    print("<-- F-Sol-M",wm.m.nbm)
                wm = wm.next
                if wm != None and wm.m == m: # simple loop already run
                    wm = wm.next                    

            else:   # otherNd not final
                stack.append(wm)
                st_bis.append((nd,n_ord,nd.ist,m.state,totL,totQL))
                totL = totL + m.length
                totQL = totQL + m.qual
                nd.ist = len(stack)-1
                if m.state == 0:
                    m.state = 4
                elif m.state == 1:
                    if otherNd == m.nd2:
                        m.state = 2 # Return way, direct sense
                    else:
                        m.state = 3 # reverse sense
                else:
                    m.state = 4 # Return way used twice
                nd = otherNd
                wm = nd.headWM
    # wm == None
    elif len(stack) == 0: # all choices exhausted
        Go = False
    else:  # node exhausted
        wm = stack.pop()
        m = wm.m
        if deb >= 2:
            print('-> POP',m.nbm)
        (nd,n_ord,ist,state,totL,totQL) = st_bis.pop()
        nd.ist = ist
        m.state = state
        wm = wm.next
        if wm != None and wm.m == m: # simple loop already run
            wm = wm.next
                    
        if len(stack)==0 and wm!=None and wm.next==None and wm.m.state==0:
            Go = False  # avoid last way from StartNode for roundtrips
# end main loop

if not parse:  # Mise en forme des solutions
  print('\n',nSol, "combination(s)\n")
  listFile.write(str(nSol)+" combination(s)\n\n")

if not parse and nSol > 0:  # output solutions
    print("Shortest : L = {:.2f} km".format(minL))
    print("Longest : L = {:.2f} km".format(maxL))

    TS = [] # Final array of tracks, sorted by length
    Nres = 0  # Nb tracks in TS
    
    # Solutions managed by slices, then by decreasing quality
    it = -1     # index actual slice
    Noc = 0     # number of tracks in actual slice
    Nex = 0

    hh = nSol  # remaining heap height
    while hh > 0:
        NewSol = HSol[1]
        if NewSol.t > it:  # new slice

            # sort of previous slice by length
            ideb = Nres
            for i in range(Noc):
                Sol = HSol[Toc[i].adoc]
                TS.append(None)
                j = Nres
                while j > ideb and Sol.l < TS[j-1].l:
                    TS[j] = TS[j-1]
                    j -= 1
                TS[j] = Sol
                Nres += 1
            
            # init new slice
            it = NewSol.t
            N = Nb_tracks[it]
            Toc = []
            for i in range(N+1):
                Toc.append(None)
            Noc = 0  # Nb tracks stored for this slice
            Nex = 0  # Nb tracks seen
            Dmin = 20.0
            Imin = 0

        Nobj = objc(hh) # New track, hh = his future adress
        Nex += 1

        # diversity of new track vs previous tracks of the same slice
        Dmin_obj = 20.0
        for iq in range(Noc):
            if Noc < N or (Dmin_obj > Dmin and iq != Imin):
                d = NewSol.q + fdiv(Toc[iq].adoc)
                Nobj.td.append(d)
                Dmin_obj = min(d,Dmin_obj)
            else:  # diversity not useful
                Nobj.td.append(20.0)
        if Dmin_obj < Dmin:
            Dmin = Dmin_obj
            Imin = Noc
        Nobj.Dmin = Dmin
        Nobj.Imin = Imin
        Toc[Noc] = Nobj

        if Noc == N and Dmin_obj > Dmin:
            # track in Imin removed by shifting of next ones
            for iq in range(Imin,N): # shift
                Nobj = Toc[iq+1]
                for i in range(Imin,iq):
                    Nobj.td[i] = Nobj.td[i+1]
                Nobj.td.pop()
                Dmin_obj = Nobj.td[0]  # new min diversity of this track
                for i in range(1,iq):
                    Dmin_obj = min(Dmin_obj, Nobj.td[i])
                if Dmin_obj < Toc[iq-1].Dmin: # new min track
                    Nobj.Dmin = Dmin_obj
                    Nobj.Imin = iq
                else:
                    Nobj.Dmin = Toc[iq-1].Dmin
                    Nobj.Imin = Toc[iq-1].Imin
                Toc[iq] = Nobj

        if Noc == N:
            Dmin = Toc[N-1].Dmin
            Imin = Toc[N-1].Imin
        else:
            Noc += 1

        Sol = HSol[hh]
        HSol[hh] = HSol[1]  # solution put at its final place
        hh -= 1
        # Last Sol put in the heaptree from the root
        freep = 1   # free place
        Go = hh > 1
        while Go:
            fp2 = 2*freep
            if fp2 > hh:
                Go = False
            else:
                if fp2 < hh and beforeSol(HSol[fp2+1], HSol[fp2]):
                    fp2 += 1
                if beforeSol(Sol,HSol[fp2]):
                    Go = False
                else:
                    HSol[freep] = HSol[fp2]
                    freep = fp2
                    fp2 = 2*freep
        HSol[freep] = Sol
        # New best solution in HSol[1]

    # sort of last slice by length
    ideb = Nres
    for i in range(Noc):
        Sol = HSol[Toc[i].adoc]
        TS.append(None)
        j = Nres
        while j > ideb and Sol.l < TS[j-1].l:
            TS[j] = TS[j-1]
            j -= 1
        TS[j] = Sol
        Nres += 1
     
    # solutions output
    sd = []
    for jt in range(Nres):
        slg = '{:.1f}'.format(100+TS[jt].l).replace('.',',')
        slg = slg[-4:]
        if slg in sd:   # tracks with same length : add a letter A,B,...
            slg = slg+chr(CS)
            CS += 1
        else:
            sd.append(slg)
            CS = 65  # code of 'A'
        listFile.write('L = '+slg+'km Qual = {:.1f}\n'.format(TS[jt].q))
        GPXName = SolName+'_'+slg+'km.gpx'
        GPXFile = open(GPXName,'w')
        initGPX(GPXFile)
        outSol(GPXFile,GPXName[:-4],TS[jt].s)
        GPXFile.write('</gpx>\n')
        GPXFile.close()
    listFile.write("\n"+str(Nres)+" output combination(s)\n")
    listFile.write("GPX files : "+SolName+"_....km.gpx\n")
    print('\n',Nres, "output combination(s), listed on", outputList)

if parse:
    print("End Analysis")
else:
  listFile.close()
print(' ')




