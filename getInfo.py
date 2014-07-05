#!/usr/bin/python

import os
import random
import re
import shlex
import subprocess
import xml.dom.minidom
from vidKeys import *

def getVinfo(vid):
  (author, title, width, height, desc, views, upDate, srcURL, encURL) = ('', '', '0', '0', '', '0', '0', '', '')

  fileName = '/tmp/vids/viddler-' + vid
  os.system('wget --timeout=30 --tries=3 -q -O ' + fileName + ' "http://api.viddler.com/rest/v1/?method=viddler.videos.getDetails&api_key=' + apiKey + '&video_id=' + vid + '&include_comments=0"')

  try:
    xmlDoc = xml.dom.minidom.parse(fileName)

    curNode = xmlDoc.documentElement.firstChild # should now be inside <video>
  
    while curNode:
      if curNode.tagName == 'code': # this is <error><code> -- aaa, abandon ship
        return ('', '', '0', '0', '', '0', '0', '', '')
      elif curNode.tagName == 'author':
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
      elif curNode.tagName == 'files':
        fNode = curNode.firstChild
        while fNode:
          if fNode.tagName == 'source':
            srcURL = fNode.firstChild.data
          elif fNode.tagName == 'flv':
            encURL = fNode.firstChild.data

          fNode = fNode.nextSibling
  
      curNode = curNode.nextSibling
  except:
    return (author, title, width, height, desc, views, upDate, srcURL, encURL)

  os.remove(fileName)

  return (author, title, width, height, desc, views, upDate, srcURL, encURL)
