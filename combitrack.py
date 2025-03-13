# Create combined hiking tracks from an OpenstreetMap network
# Construction de combinaisons d'itinéraires à partir d'un maillage OpenStreetMap
# Bernard HOUSSAIS - FF Randonnée 35 - bh35@orange.fr
# Release 5.7 - Mar 2025

import sys
from tkinter import *
from tkinter import ttk
import xml.sax as sax
from math import sqrt, cos

deb = 0 # 0 .. 3 : level of debug prints
Start_nodes_output = True  # output as waypoints in network GPX file

print("\nCOMBITRACK - v5.7 - March 2025\n")

maxGPXoutput = 20 # max number of GPX tracks output
                  # may be modified by nbSol not empty

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

# window for input parameters
root = Tk(className='Combitrack')
mwin = ttk.Frame(root)  # main window
mwin.grid(column=0, row=0)
messNw = ttk.Label(mwin,text="Network :")
messNw.grid(column=0, row=0)

try:
    fmem = open('.memo.txt','r')
    prevNw = fmem.readline()[:-1]  # string without newline
    prevSt = fmem.readline()[:-1]
    prevFn = fmem.readline()[:-1]
    fmem.close()
except:
    prevNw = prevSt = prevFn = ''

varNw = StringVar(mwin,prevNw)
entNw = ttk.Entry(mwin,textvariable=varNw,width=60)
entNw.grid(column=1,row=0,columnspan=4)

messSt = ttk.Label(mwin,text="  Start :")
messSt.grid(column=0, row=1)
varSt = StringVar(mwin,prevSt)
entSt = ttk.Entry(mwin,textvariable=varSt,width=60)
entSt.grid(column=1,row=1,columnspan=4)

messFn = ttk.Label(mwin,text="   Finish :\n(when #Start)")
messFn.grid(column=0, row=2)
varFn = StringVar(mwin,prevFn)
entFn = ttk.Entry(mwin,textvariable=varFn,width=60)
entFn.grid(column=1,row=2,columnspan=4)

messLm = ttk.Label(mwin,text="Lmin :\n(empty=0)")
messLm.grid(column=0, row=3)
varLm = StringVar(mwin,'')
entLm = ttk.Entry(mwin,textvariable=varLm,width=10)
entLm.grid(column=1,row=3)

messLM = ttk.Label(mwin,text=" Lmax :\n(unlimited)")
messLM.grid(column=2, row=3)
varLM = StringVar(mwin,'')
entLM = ttk.Entry(mwin,textvariable=varLM,width=10)
entLM.grid(column=3,row=3)

messNS = ttk.Label(mwin,text=" Nb Sol :\n  (all)")
messNS.grid(column=4, row=3)
varNS = StringVar(mwin,'')
entNS = ttk.Entry(mwin,textvariable=varNS,width=10)
entNS.grid(column=5,row=3)

gow = ttk.Button(mwin,text="Go !",command=root.destroy)
gow.grid(column=1,row=4)

root.mainloop()

inputOSMFile = varNw.get()
if inputOSMFile == "":  # empty network file name = Cancel button
    sys.exit()
startName = varSt.get()
finalName = varFn.get()
if inputOSMFile[-4:] != '.osm':
    inputOSMFile += '.osm'
print ("OSM network: ", inputOSMFile);
rootName = inputOSMFile[:-4]
fullName = inputOSMFile

fmem = open('.memo.txt','w')
fmem.write(fullName+'\n'+startName+'\n'+finalName+'\n')
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
    outputList = "C_"+rootName+".txt"  # list of combined tracks
    outputGPXFile = "C_"+rootName+".gpx"  # combined tracks in GPX format
else:
    netGPXFile = rootName.replace('/','/_')+".gpx"
    outputList = rootName.replace('/','/C_')+".txt"
    outputGPXFile = rootName.replace('/','/C_')+".gpx"

startNode = None
sLatLon = False
latS=0.0
if len(startName) > 0 and startName[0] == '(': # S="(Lat,Lon)" format
    try:
        (latS,lonS) = eval(startName)
        sLatLon = True
        distS = 999.0 # to find nearest node
    except:
        print("\nStart : bad format for lat,lon :",startName)
        startName = ""

finalNode = None
fLatLon = False
if len(finalName) > 0 and finalName[0] == '(': # F="(Lat,Lon)"
    try:
        (latF,lonF) = eval(finalName)
        fLatLon = True
        distF = 999.0 # to find nearest node
    except:
        print("\nFinish : bad format for lat,lon :",finalName)
        finalName = ""

if varLm.get() == '':
    lgMin = 0.0
else:
    try:
        lgMin = eval(varLm.get().replace(',','.'))
    except:
        print("\nLMIN : bad format")
        lgMin = 0.0

if varLM.get() == '':
    lgMax = 999.0
else:
    try:
        lgMax = eval(varLM.get().replace(',','.'))
    except:
        print("\nLMAX : bad format")
        lgMax = 999.0

lgMod = lgMin != 0.0 or lgMax != 999.0

allTracks = 99999
if varNS.get() == '':
    maxBest = allTracks
else:
    try:
        maxBest = min(int(eval(varNS.get())),allTracks)
    except:
        print("\nNB SOL : bad format")
        maxBest = 0
    maxGPXoutput = maxBest # when nbSol not empty
# keep and output "maxBest" best tracks

def norm_string (s1): # s1 : string to normalize
    s2 = ""
    i1 = 0
    while i1 < len(s1):
        c1 = s1[i1]
        # print(c1,ord(c1))
        if c1>='A' and c1<='Z':
            c1 = chr(ord(c1)+32)
        elif c1=='é' or c1=='è' or c1=='ê' or c1=='ë' or c1=='É':
            c1 = 'e'
        elif c1=='à' or c1=='â':
            c1 = 'a'
        elif c1=='ô':
            c1 = 'o'
        elif c1=='ù' or c1=='û':
            c1 = 'u'
        elif c1=='ç':
            c1 = 'c'
        elif c1<'0' or c1>'9' and c1<'A' or c1>'Z' and c1<'a' or c1>'z':
            c1 = ' '
        if c1 == 't' and i1 >= 4 and s2[-4:] == 'sain':
            s2 = s2[:-3]+'t'     # saint => st
        elif c1 != ' ':
            s2 = s2+c1
        i1 = i1+1
    # print("Norm :", s2)
    return s2

normSN = norm_string(startName)
lgSN = len(normSN)
normFN = norm_string(finalName)
lgFN = len(normFN)

def setSFNodes (nd):
    # adjust Start and Final nodes according to given new node
    global startNode,finalNode,lgSN,lgFN,sLatLon,fLatLon,distS,distF
    if nd.name != "":
        nnm = norm_string(nd.name)
        if lgSN > 0 and normSN == nnm[:lgSN]:
            startNode = nd
        if lgFN > 0 and normFN == nnm[:lgFN]:
            finalNode = nd
    else:  # no name
        if sLatLon:
            dist = (nd.lat-latS)**2+(nd.lon-lonS)**2
            if dist < distS:
                startNode = nd
                distS = dist
        if fLatLon:
            dist = (nd.lat-latF)**2+(nd.lon-lonF)**2
            if dist < distF:
                finalNode = nd
                distF = dist

class DictHandler(sax.handler.ContentHandler):

    def __init__(self): 
        self.inWay = False
        self.inNode = False
        
    def setDb(self, db):
        self.db = db


    def startElement(self, name, attrs): 
        # new element in osm file
        #global sLatLon, fLatLon, latS, lonS, latF, lonF

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
          setSFNodes(self.newNode)
          if self.newNode.name != "":
              self.newNode.nbArc = 99  # start/final nodes treated as a connections
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

class initDb():
    def __init__(self,sLatLon,latS):
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
    gf.write('creator="Combitrack - Bernard Houssais"\n')
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
    return(nd)    # last node

def outSol(gf,numSol,sol):
    gf.write('<trk> <name> '+trackName+str(100+numSol)[1:]+' </name>\n')
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
db = initDb(sLatLon,latS)
readDb(osmFile,db)
osmFile.close()

if startName == "" and not sLatLon:
    maxBest = 0
if maxBest > 0:
    if startNode == None:
        print('\nBEWARE : unknown start node "'+startName+'"\n')
        maxBest = 0
    else:
        if startNode.refNd != "":
            startNode = db.nodesDict[startNode.refNd]
        startNode.nbArc = 99 # treated as a connection
    if finalNode == None:
        if finalName != "":
            print('\nBEWARE : unknown finish node "'+finalName+'"\n')
            maxBest = 0
    else:
        if finalNode.refNd != "":
            finalNode = db.nodesDict[finalNode.refNd]
        finalNode.nbArc = 99 # treated as a connection
        
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
    print("\nPossible Start/Finish points :")
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

fN = finalNode # for distance from nd to final node
if fN == None:
    fN = startNode

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
        if fN != None:
          nd.dist2Final=lgMax-sqrt((coefLat*(nd.lat-fN.lat))**2+(coefLon*(nd.lon-fN.lon))**2)
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
                    pwmRet2 = None
                    # connect other end of merged way (node nn), even for loops
                    lastWM = nn.headWM # search ways starting from nn
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
  listFile = open(outputList,'w')
  listFile.write('Network: '+inputOSMFile+'\n\n')
  if maxBest >= allTracks:
    smax = "All"
  else:
    smax = str(maxBest)
  if startNode.name == "":
      startNode.name = str(startNode.idn)
  if finalNode != None and finalNode.name == "":
      finalNode.name = str(finalNode.idn)
  fmem = open('.memo.txt','w')
  fmem.write(fullName+'\n')
  if sLatLon:
      sAff = '('+startNode.slat+','+startNode.slon+')'
  else:
      sAff = startNode.name
  fmem.write(sAff+'\n')
  roundtrip = finalNode == None or finalNode == startNode
  if roundtrip:
      finalNode = startNode
      print(smax,"roundtrip(s) from", sAff)
      listFile.write(smax+" roundtrips from "+sAff+'\n')
  else:
      if fLatLon:
          fAff = '('+finalNode.slat+','+finalNode.slon+')'
      else:
          fAff = finalNode.name
      print(smax,"track(s) between",sAff,"and",fAff)
      listFile.write(smax+" tracks between "+sAff+" and "+fAff+'\n')
      fmem.write(fAff)
  if lgMod:
      if lgMax < 998.999:  # when no upper limit, lgMax = 999
          print(' Length between {:.2f} and {:.2f} km'.format(lgMin,lgMax))
          listFile.write(' Length between {:.2f} and {:.2f} km'.format(lgMin,lgMax)+'\n')
      else:
          print(' Length at least {:.2f} km'.format(lgMin))
          listFile.write(' Length at least {:.2f} km\n'.format(lgMin))

  listFile.write('\n')
  fmem.write('\n')
  fmem.close()

                #   MAIN LOOP 
  nSol = 0  # number of computed solutions
  nBest = 0  # number of stored solutions
  heapQ = [0.0]  # best tracks are stored in a heap tree
  bestL = [0.0]     # heap tree is an array [1:maxBest]
  bestSol = [None]

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
        #  print('M',m.nbm, '-', n_ord, '>', n_orde, m.state,direct)
        okWay = m.state < 2 or roundtrip and m.state < 4
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
            if otherNd == finalNode:
                SolL = totL + m.length
                if SolL >= lgMin:   # Solution found
                    nSol = nSol+1
                    totQ = (totQL+m.qual)/SolL
                    if nSol % 10000 == 0:
                        print(nSol," solutions now")
                    totQ = (totQL+m.qual)/SolL
                    if SolL < minL:
                        minL = SolL
                        minQ = totQ
                    if SolL > maxL:
                        maxL = SolL
                        maxQ = totQ
                    stSol = stack[:]
                    stSol.append(wm)
                    if deb >= 1:
                        print("SOL",nSol,'L={:.2f} Q={:.2f}'.format(SolL,totQ))
                        t=[]  # print ways of the solution
                        for ws in stSol:
                            t.append(ws.m.nbm)
                        print(t,'\n')                        
                    # Store the solution in the heap tree
                    if nBest < maxBest:  # tree not full
                        nBest = nBest+1
                        heapQ.append(0.0)
                        bestL.append(0.0)
                        bestSol.append(None)
                        freep = nBest   # free place
                        fp2 = freep//2
                        while freep > 1 and totQ < heapQ[fp2]:
                            heapQ[freep] = heapQ[fp2]
                            bestL[freep] = bestL[fp2]
                            bestSol[freep] = bestSol[fp2]
                            freep = fp2
                            fp2 = freep//2
                        heapQ[freep] = totQ
                        bestL[freep] = SolL
                        bestSol[freep] = stSol
                    elif totQ > heapQ[1]: # better solution put in the tree
                        freep = 1
                        Go2 = nBest > 1
                        while Go2:
                            fp2 = 2*freep
                            if fp2 > nBest:
                                Go2 = False
                            else:
                                if fp2 < nBest and heapQ[fp2+1] < heapQ[fp2]:
                                    fp2 = fp2+1
                                if totQ < heapQ[fp2]:
                                    Go2 = False
                                else:
                                    heapQ[freep] = heapQ[fp2]
                                    bestL[freep] = bestL[fp2]
                                    bestSol[freep] = bestSol[fp2]
                                    freep = fp2
                                    fp2 = 2*freep
                        heapQ[freep] = totQ
                        bestL[freep] = SolL
                        bestSol[freep] = stSol

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

        if len(stack)==0 and roundtrip and wm!=None and wm.next==None and wm.m.state==0:
            Go = False  # shortcut for last way from StartNode for roundtrips
# end main loop

if not parse:
  print('\n',nSol, "combination(s)\n")
  listFile.write(str(nSol)+" combination(s)\n")

if not parse and nSol > 0:
  # output best solutions, better at the end
  nGPX = min(nBest,maxGPXoutput)
  if nBest == 1:
    print("GPX of best combination :", outputGPXFile)
  else:      
    print("GPX of best ",nGPX," :",outputGPXFile)
    print("Full list on ", outputList)
  cGPXFile = open(outputGPXFile,'w')
  initGPX(cGPXFile)
  print("\nShortest : L = {:.2f} km".format(minL),' Qual = {:.1f}'.format(minQ))
  print("Longest : L = {:.2f} km".format(maxL),' Qual = {:.1f}'.format(maxQ))
  if nBest == 1:
      print(" Best one :\n")
  else:
      print(" Best", min(nBest,3)," :")

  while nBest > 0:
    if nBest <= 3:
      print(nBest,': L = {:.2f} km'.format(bestL[1]),' Qual = {:.1f}'.format(heapQ[1]))
    listFile.write(str(nBest)+': L = {:.2f} km'.format(bestL[1])+' Qual = {:.1f}\n'.format(heapQ[1]))
    if nBest <= maxGPXoutput: # reverse order, best tracks over others
        outSol(cGPXFile,nBest,bestSol[1])
    nBest = nBest-1
    if nBest > 0:
        freep = 1
        Go2 = nBest > 1
        while Go2:
            fp2 = 2*freep
            if fp2 > nBest:
                Go2 = False
            else:
                if fp2 < nBest and heapQ[fp2+1] < heapQ[fp2]:
                    fp2 = fp2+1
                if heapQ[nBest+1] < heapQ[fp2]:
                    Go2 = False
                else:
                    heapQ[freep] = heapQ[fp2]
                    bestL[freep] = bestL[fp2]
                    bestSol[freep] = bestSol[fp2]
                    freep = fp2
                    fp2 = 2*freep
        heapQ[freep] = heapQ[nBest+1]
        bestL[freep] = bestL[nBest+1]
        bestSol[freep] = bestSol[nBest+1]
  cGPXFile.write('</gpx>\n')
  cGPXFile.close()
if parse:
    print("End analysis")
else:
  listFile.close()
print(" ")
