#!/usr/bin/python

import os
import random
import re
import shlex
import subprocess
import xml.dom.minidom
from vidKeys import *

# Type 1: by URL
# Type 2: by ID

def getVinfo(ident, type):
  fileName = '/tmp/vid' + `int(random.random()*9999)`
  (author, id, title, width, height, desc, views, upDate) = ('', '', '', '0', '0', '', '0', '0')

  if type == 1:
    os.system('wget --timeout=30 --tries=3 -q -O ' + fileName + ' "http://api.viddler.com/rest/v1/?method=viddler.videos.getDetailsByUrl&api_key=' + apiKey + '&url=' + ident + '&include_comments=0"')
  else:
    os.system('wget --timeout=30 --tries=3 -q -O ' + fileName + ' "http://api.viddler.com/rest/v1/?method=viddler.videos.getDetails&api_key=' + apiKey + '&video_id=' + ident + '&include_comments=0"')

  try:
    xmlDoc = xml.dom.minidom.parse(fileName)

    curNode = xmlDoc.documentElement.firstChild # should now be inside <video>
  
    while curNode:
      if curNode.tagName == 'author':
        author = curNode.firstChild.data
      elif curNode.tagName == 'id':
        id = curNode.firstChild.data
      elif curNode.tagName == 'title':
        if curNode.firstChild != None: # odd ones are blank. viddler bug
          title = curNode.firstChild.data
      elif curNode.tagName == 'width':
        width = curNode.firstChild.data
      elif curNode.tagName == 'height':
        height = curNode.firstChild.data
      elif curNode.tagName == 'description':
        # This is optional, unlike everything else
        if curNode.firstChild == None:
          desc = ''
        else:
          desc = curNode.firstChild.data
      elif curNode.tagName == 'view_count':
        views = curNode.firstChild.data
      elif curNode.tagName == 'upload_time':
        upDate = curNode.firstChild.data
  
      curNode = curNode.nextSibling
  except:
    return (author, id, title, width, height, desc, views, upDate)

  os.remove(fileName)

  return (author, id, title, width, height, desc, views, upDate)


def getRes(fName):
  (result,result2) = ('-','-')

  p = subprocess.Popen(shlex.split('/usr/bin/ffmpeg -i ' + fName), stderr=subprocess.PIPE)
  for line in p.stderr:
    m = re.search('^    Stream \S+: Video: \S+, \S+, (\d+x\d+)[, ]', line)
    if m:
      result = m.group(1)

    # backup plan
    m = re.search('Could not find codec parameters \(Video: \S+, (\d+x\d+)\)', line)
    if m:
      result2 = m.group(1)

  if result == '-':
    result = result2

  return result
