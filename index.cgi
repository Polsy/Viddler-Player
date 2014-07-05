#!/usr/bin/python

import cgi
import codecs
import commands
import Cookie
import httplib
import os
import re
import sys
import time

from getInfo2 import *
from vidKeys2 import *

embedTxt = '<object classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000" width="WIDTH" height="HEIGHT" id="viddler"><param name="flashvars" value="FLASHVARS" /><param name="movie" value="http://www.viddler.com/PLAYER/VIDEOID/" /><param name="allowScriptAccess" value="always" /><param name="allowFullScreen" value="true" /><param name="wmode" value="transparent" /><embed id="vEmbed" src="http://www.viddler.com/PLAYER/VIDEOID/" width="WIDTH" height="HEIGHT" type="application/x-shockwave-flash" allowScriptAccess="always" flashvars="FLASHVARS" allowFullScreen="true" wmode="transparent" name="viddler" ></embed></object>'

vidFormTxt = 'Viddler username: <input name="user" size=15 maxlength=15 type="text" value="FUSER"> Video number: <input name="video" size=4 maxlength=4 type="text" value="FVIDEO"><br>\nOr paste URL: <input name="vurl" type="text" size=64 value="FURL"><br><br>\nStart video at (seconds): <input name="start" size=4 maxlength=4 type="text" value="START"><br>\n<input type="checkbox" name="useSimple"FSIMPLE>Use simple player<br>\n<input type="checkbox" name="origRes"FRES>Force source video resolution<br>\n'

setFormTxt = 'Original video size: <input type="radio" name="setOrigRes" value="1"OR1>Always on <input type="radio" name="setOrigRes" value="0"OR0>Always off <input type="radio" name="setOrigRes" value="-1"OR-1>Use URL setting<br>'
setFormTxt += 'Use simple player: <input type="radio" name="setUseSimple" value="1"US1>Always on <input type="radio" name="setUseSimple" value="0"US0>Always off <input type="radio" name="setUseSimple" value="-1"US-1>Use URL setting<br>'
setFormTxt += '<input type="checkbox" name="setAutoPlay"CAP> Autoplay videos<br>'

errState = 0

# Read cookie header
cJar = Cookie.SimpleCookie()
if os.environ.has_key('HTTP_COOKIE'):
  cJar.load(os.environ['HTTP_COOKIE'])

# Save the current URL for going back to (possibly)
setFormTxt += '<input type="hidden" name="returl" value="http://' + os.environ['SERVER_NAME'] + os.environ['REQUEST_URI'] + '">'

# Read what's there
# - Override original resolution?
if cJar.has_key('cOrigRes'):
  try:
    cOrigRes = int(cJar['cOrigRes'].value)
  except:
    cOrigRes = -1
else:
  cOrigRes = -1
# - Override simple player?
if cJar.has_key('cUseSimple'):
  try:
    cUseSimple = int(cJar['cUseSimple'].value)
  except:
    cUseSimple = -1
else:
  cUseSimple = -1
# - Autoplay?
if cJar.has_key('cAutoPlay'):
  try:
    cAutoPlay = int(cJar['cAutoPlay'].value)
  except:
    cAutoPlay = 0
else:
  cAutoPlay = 0

# Read posted form contents
form = cgi.FieldStorage()

# Settings form or video form?
if form.getfirst('settings'):
  expireStr = time.strftime('%a, %d %b %Y %H:%M:%S', time.gmtime(time.time() + (60*60*24*365*2)))

  try:
    newOrigRes = int(form.getfirst('setOrigRes'))
    if newOrigRes >= -1 and newOrigRes <= 1:
      cOrigRes = newOrigRes
      cJar['cOrigRes'] = cOrigRes
      cJar['cOrigRes']['path'] = '/'
      cJar['cOrigRes']['expires'] = expireStr
  except:
    pass

  try:
    newUseSimple = int(form.getfirst('setUseSimple'))
    if newUseSimple >= -1 and newUseSimple <= 1:
      cUseSimple = newUseSimple
      cJar['cUseSimple'] = cUseSimple
      cJar['cUseSimple']['path'] = '/'
      cJar['cUseSimple']['expires'] = expireStr
  except:
    pass

  newAutoPlay = form.getfirst('setAutoPlay')
  if newAutoPlay == 'on':
    cAutoPlay = 1
  else:
    cAutoPlay = 0

  cJar['cAutoPlay'] = cAutoPlay
  cJar['cAutoPlay']['path'] = '/'
  cJar['cAutoPlay']['expires'] = expireStr

  # Set cookies
  if form.getfirst('settings'):
    print cJar.output()

  # and bounce back to where you were
  prevLoc = form.getfirst('returl')
  if prevLoc:
    print 'Status: 302 Temporarily moved'
    print 'Location: ' + prevLoc + '\n'
    sys.exit(0)

(vidUser, vidVid, vNum) = ('', '', '')
 
# Figure out real Viddler URL from posted user/video number/URL
# or use /v/ID
vidUrl = form.getfirst('vurl', '')
if vidUrl:
  uMatch = re.search('viddler.com/(?:explore/)?([^/]+)/videos/(\d+)', vidUrl)
  if uMatch:
    (vidUser, vidVid) = uMatch.groups()
  else:
    uMatch = re.search('viddler.com/v/([0-9a-z]+)', vidUrl)
    if uMatch:
      (vidUser, vNum) = ('_', uMatch.group(1))  
    else:
      errState = 2
else:
  vidUser = form.getfirst('user', '')
  vidVid = form.getfirst('video', '')

vidUser = re.sub('[^-A-Za-z0-9_]+', '', vidUser)
vidVid = re.sub('[^0-9]+', '', vidVid)

if vidUser and vidVid:
  # Convert to vNum, or try to
  cacheRFile = 'cache/R/' + vidUser + '-' + vidVid
  if os.path.exists(cacheRFile):
    f = open(cacheRFile, 'r')
    vNum = f.read()
    f.close()
  else:
    hReq = httplib.HTTPConnection('www.viddler.com')
    hReq.request('HEAD', '/explore/' + vidUser + '/videos/' + vidVid + '/')
    hRes = hReq.getresponse()
    if hRes.getheader('Location'):
      newURL = hRes.getheader('Location')
      if re.search('viddler.com/v/', newURL):
        f = open(cacheRFile, 'w')
        vNum = re.search('viddler.com/v/([a-z0-9]+)', newURL).group(1)
        f.write(vNum)
        f.close()

if vNum:
  vPage = 'http://www.viddler.com/v/' + vNum
elif vidUser:
  # Trailing slash I guess is the official format as the API demands it
  vPage = 'http://www.viddler.com/explore/' + vidUser + '/videos/' + vidVid + '/'
else:
  vPage = ''

# Select player type from form (or cookies)
if cUseSimple == -1:
  useSimple = form.getfirst('useSimple', 0)
else:
  useSimple = cUseSimple

# Select original resolution from form (or cookies)
if cOrigRes == -1:
  origRes = form.getfirst('origRes')
  if origRes == None:
    origRes = form.getfirst('unlimit640', 0)
else:
  origRes = cOrigRes

# Get start time
startTime = form.getfirst('start', '')
if startTime:
  startTime = re.sub('[^0-9]+', '', startTime)

# Force resolution?
fXres = form.getfirst('xRes', '0')
fYres = form.getfirst('yRes', '0')
if fXres != '0':
  origRes = 1

vTitle = ''
vSError = ''
vVersion = 0

if (vidUser and vidVid) or vNum:
  if vNum:
    cacheFile = 'cache/' + vNum
  else:
    cacheFile = 'cache/' + vidUser.lower() + vidVid

  if os.path.exists(cacheFile):
    f = codecs.open(cacheFile, 'r', 'utf-8')
    vVersion = f.readline().rstrip()
    if(len(vVersion) > 1):
      vNum = vVersion
      vVersion = 0
    else:
      vVersion = int(vVersion)
      if vVersion < 3:
        vNum = f.readline().rstrip()

    vSourceExt = f.readline().rstrip()

    if vVersion != 0:
      vEWidth = f.readline().rstrip()
      vEHeight = f.readline().rstrip()
      vSError = f.readline().rstrip()
    else:
      (vEWidth, vEHeight) = ('0', '0')

    vSWidth = f.readline().rstrip()
    vSHeight = f.readline().rstrip()

    vUpper = f.readline().rstrip()
    vTitle = f.readline().rstrip()
    vDesc = f.readline().rstrip()
    vViews = f.readline().rstrip()

    (vFLVHD, vSourceL, vEncodedL) = ('', '', '')
    if vVersion == 2:
      vFLVHD = f.readline().rstrip()
    elif vVersion == 3:
      vSourceL = f.readline().rstrip()
      vEncodedL = f.readline().rstrip()

    f.close()

    # reread info (mainly to update view count) - always do this if views < 5 to stop 'wow I was the first view!' posts
    if vVersion == 0 or int(vViews) < 5 or (time.time() - os.path.getmtime(cacheFile)) > 2*60*60:
      (newVUpper, newVTitle, newVSWidth, newVSHeight, newVEWidth, newVEHeight, newVDesc, newVViews, newVUpDate, newVSourceL, newVSourceExt, newVEncodedL, newVEncodedExt) = getVinfo(vNum)

      if newVUpper: # failure isn't particularly problematic
        if newVSWidth == '0': # keep the old res
          (newVSWidth, newVSHeight) = (vSWidth, vSHeight)
        if newVEWidth == '0': # keep the old res
          (newVEWidth, newVEHeight) = (vEWidth, vEHeight)

        (vUpper, vTitle, vSWidth, vSHeight, vEWidth, vEHeight, vDesc, vViews, vSourceL, vEncodedL) = (newVUpper, newVTitle, newVSWidth, newVSHeight, newVEWidth, newVEHeight, newVDesc, newVViews, newVSourceL, newVEncodedL)

      if not newVUpper and vVersion != 3:
        pass # don't destroy existing user/video cache files, even if the video no longer exists
      else:
        f = codecs.open(cacheFile, 'w', 'utf-8')
        f.write('3\n') # version
        f.write('*\n') # vExt, for compatibility
        f.write(vEWidth + '\n')
        f.write(vEHeight + '\n')
        f.write(vSError + '\n')
        f.write(vSWidth + '\n')
        f.write(vSHeight + '\n')
        f.write(vUpper + '\n')
        f.write(vTitle + '\n')
        f.write(vDesc + '\n')
        f.write(vViews + '\n')
        f.write(vSourceL + '\n')
        f.write(vEncodedL + '\n')
        f.close()

  else: # new video entirely
    (vUpper, vTitle, vSWidth, vSHeight, vEWidth, vEHeight, vDesc, vViews, vUpDate, vSourceL, vSourceExt, vEncodedL, vEncodedExt) = getVinfo(vNum)

    if vUpper: # else it failed
      if vSWidth == '0':
        (vSWidth, vSHeight) = (vEWidth, vEHeight)
        vSError = 'copied from encoded'
 
      if vSWidth == '0': # No file information returned for some reason - assume 640x480
        (vEWidth, vEHeight) = ('640', '480')
        vSError = 'sorry, can\'t detect resolution at all - using 640x480'
  
      f = codecs.open(cacheFile, 'w', 'utf-8')
      f.write('3\n') # version
      # I have the file extension available but it's not actually useful now
      vSourceExt = '*'
      f.write('*\n')
      f.write(vEWidth + '\n')
      f.write(vEHeight + '\n')
      f.write(vSError + '\n')
      f.write(vSWidth + '\n')
      f.write(vSHeight + '\n')
      f.write(vUpper + '\n')
      f.write(vTitle + '\n')
      f.write(vDesc + '\n')
      f.write(vViews + '\n')
      f.write(vSourceL + '\n')
      f.write(vEncodedL + '\n')
      f.close()
    else:
      errState = 1 

print "Content-Type: text/html; charset=utf-8\n"

print '<html>'
print '<head>'
if vTitle:
  print '  <title>' + vTitle.encode('utf-8') + ' - by ' + vUpper.encode('utf-8') + '</title>'
else:
  print '  <title>Viddler Player</title>'
print '  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
print '</head>'

print """<body bgcolor="#CCCCCC">
<script language="JavaScript">
var trueW, trueH;

function fullify() {
  d = document.getElementById("topDiv");
  d.parentNode.removeChild(d);
  d = document.getElementById("bottomDiv");
  d.parentNode.removeChild(d);
  v = document.getElementById("vEmbed");
  if(v == null) { v = document.getElementById("viddler"); }
  v.width = document.body.clientWidth-20;
  v.height = document.body.clientHeight-16;
  document.body.bgColor = "black";

  // Hide scrollbars
  document.body.style.overflow = "hidden";
}

function szChange() {
  s = document.getElementById("pickSz");
  v = document.getElementById("vEmbed");
  if(v == null) { v = document.getElementById("viddler"); }

  if(s && s.value && v) {
    v.width = trueW * (s.value / 100); v.height = trueH * (s.value / 100) + 42;
  }
}

function showHideSettings() {
  sb = document.getElementById("settingsBtn");
  sd = document.getElementById("settingsDiv");
  ss = document.getElementById("settingsSpacer");
  
  if(sd.style.display == 'none') {
    sb.innerText = 'Hide Settings';
    sd.style.display = 'block';
    ss.style.display = 'none';
  } else { 
    sb.innerText = 'Show Settings';
    sd.style.display = 'none';
    ss.style.display = 'block';
  }
}
</script>

<div style="text-align: right" id="topDiv"><small><a href="#" id="settingsBtn" onclick="showHideSettings();">Show Settings</a></small>
<div id="settingsDiv" style="display: none">
<form method="GET">
"""

setFormTxt = re.sub('OR' + `cOrigRes`, ' checked', setFormTxt)
setFormTxt = re.sub('OR-?\d', '', setFormTxt)
setFormTxt = re.sub('US' + `cUseSimple`, ' checked', setFormTxt)
setFormTxt = re.sub('US-?\d', '', setFormTxt)
if cAutoPlay:
  setFormTxt = re.sub('CAP', ' checked', setFormTxt)
else:
  setFormTxt = re.sub('CAP', '', setFormTxt)

print setFormTxt

print """<input type="submit" name="settings"></form></div>
<div id="settingsSpacer"><br><br><br></div></div>
<center>"""

if errState == 1:
  print 'Sorry, there was an error getting the video details. If <a href="' + vPage + '">this</a> is definitely a valid video link, let Polsy know.<br>'
elif errState == 2:
  print 'Sorry, there was an error getting the video details. If <a href="' + vidUrl + '">' + vidUrl + '</a> is definitely a valid video link, let Polsy know.<br>'
elif (vidUser and vidVid) or vNum:
  sourceRes = 'Source resolution: ' + vSWidth + 'x' + vSHeight
  if vSError:
    sourceRes += ' (inaccurate)'
    # sourceRes += ' (err: ' + vSError + ')'

  encodedRes = 'Encoded resolution: ' + vEWidth + 'x' + vEHeight

  if origRes and vSWidth != '0':
    vWidth = vSWidth
    vHeight = vSHeight
  else:
    vWidth = vEWidth
    vHeight = vEHeight

  # Set fixed resolution
  if fXres != '0':
    vWidth = fXres
  if fYres != '0':
    vHeight = fYres

  vHeight = `int(vHeight) + 42`
  embedTxt = re.sub('WIDTH', vWidth, embedTxt)
  embedTxt = re.sub('HEIGHT', vHeight, embedTxt)

  if useSimple:
    pType = 'simple'
  else:
    pType = 'player'
  embedTxt = re.sub('PLAYER', pType, embedTxt)

  if cAutoPlay:
    embedTxt = re.sub('FLASHVARS', 'autoplay=t&FLASHVARS', embedTxt)

  if startTime:
    embedTxt = re.sub('FLASHVARS', 'offsetTime=' + startTime, embedTxt)
  else:
    embedTxt = re.sub('FLASHVARS', '', embedTxt)

  embedTxt = re.sub('VIDEOID', vNum, embedTxt)

  print embedTxt
  print '<div id="bottomDiv">'

  # Remove some extra spacing that's generated by the description
  if vDesc:
    vDesc = re.sub('^<p>(.+)</p>$', '\\1', vDesc)
    print '<br>' + vDesc.encode('utf-8')

  print '<br><br>Views: ' + vViews + '<br>\n'

  if encodedRes:
    if origRes:
      print '<b>' + sourceRes + '</b> | ' + encodedRes
    else:
      print sourceRes + ' | <b>' + encodedRes + '</b>'
  else:
    print sourceRes

  print '<br><br>'
  print '<a href="' + vPage + '">Viddler page</a>',

  if vSourceExt != '':
    if vSourceExt == '*': # v3+, have full paths
      if vSourceL and vEncodedL:
        print 'Download:',
      elif vSourceL or vEncodedL: # it's possible neither exist
        print 'Download',

      if vSourceL:
        print '<a href="' + vSourceL + '">Original</a>'
      if vEncodedL:
        print '<a href="' + vEncodedL + '">Flash</a>'
    else:
      if vSourceExt == 'flv' or vSourceExt[0] == '!':
        print '<a href="' + vPage[:-1] + '.flv">Download Flash</a>'
      else:
        if vFLVHD:
          print 'Download: <a href="' + vPage[:-1] + '.' + vSourceExt + '">Original</a> <a href="' + vFLVHD + '">Flash HD</a> <a href="' + vPage[:-1] + '.flv">Flash SD</a>'
        else:
          print 'Download: <a href="' + vPage[:-1] + '.' + vSourceExt + '">Original</a> <a href="' + vPage[:-1] + '.flv">Flash</a>'

  print '<br><script language="JavaScript">trueW=' + vWidth + '; trueH=' + str(int(vHeight)-42) + '; document.write(\'<select id="pickSz" onchange="szChange();");"><option value="75">75%<option value="100" selected>100%<option value="200">200%</select> <button onclick="fullify();">Fill browser window</button>\');</script>'

print """<br><br><br>
<form method="GET">"""

if vidUser == '_':
  vidUser = vUpper
vidFormTxt = re.sub('FUSER', vidUser, vidFormTxt)
vidFormTxt = re.sub('FVIDEO', vidVid, vidFormTxt)
vidFormTxt = re.sub('FURL', vPage, vidFormTxt)
if useSimple:
  vidFormTxt = re.sub('FSIMPLE', ' checked', vidFormTxt)
else:
  vidFormTxt = re.sub('FSIMPLE', '', vidFormTxt)
if origRes:
  vidFormTxt = re.sub('FRES', ' checked', vidFormTxt)
else:
  vidFormTxt = re.sub('FRES', '', vidFormTxt)
vidFormTxt = re.sub('START', startTime, vidFormTxt)
print vidFormTxt

print """<br><input id="btnSubmit" type="submit"></form>
<br><br><small><a href="mailto:polsylp@polsy.org.uk">polsylp@polsy.org.uk</a></small>
</div>
</center>
</body>
</html>"""
