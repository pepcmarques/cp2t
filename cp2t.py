#!/usr/bin/env python
# -*- encoding: UTF-8 -*-

import codecs
import htmlentitydefs
import os
import sys
import getopt
import time

import cv2
import math

from BeautifulSoup import BeautifulSoup
from PIL import Image, ImageDraw
from tempfile import NamedTemporaryFile

def line(line):
    p1 = [line[0],line[1]]
    p2 = [line[2],line[3]]
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0]*p2[1] - p2[0]*p1[1])
    return A, B, -C

def intersection(L1, L2):
    D  = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return x,y
    else:
        return False

def htmlescape(txt):
    mapa = {}
    for (k,v) in htmlentitydefs.entitydefs.items():
       mapa[v.decode('iso-8859-1')] = k
    sai = ''.join(['&{c};'.format(c=mapa.get(c)) if c in mapa else c for c in txt])
    return(sai)

class PDF_page:
   def __init__(self, filename, outputfile, file_format, debug):
      #
      tf = NamedTemporaryFile()
      #
      year = int(filename.split("/")[-1][:4])
      if year < 2002:
         comando = "pdftotext -htmlmeta -bbox %s %s" %(filename,tf.name)
      else:
         comando = "pdftotext -htmlmeta -bbox -raw %s %s" %(filename,tf.name)
      #
      os.system(comando)
      #
      self.filename       = filename
      self.file_format    = file_format
      self.out_file       = outputfile
      self.debug          = debug
      self.html_file      = self.filename[:-4]+".html"
      self.png_file       = self.filename[:-4]+".png"
      self.text_file      = self.filename[:-4]+".txt"
      self.size           = {}
      self.size["width"]  = 0
      self.size["height"] = 0
      #
      self.dminw = 9999
      self.dmaxw = 0
      self.dmedw = 0
      #
      self.header             = {}
      self.header["exists"]   = False
      self.header["idxb"]     = 0.0000
      self.header["idxe"]     = 0.0000
      self.header["x1"] = 0
      self.header["y1"] = 0
      self.header["x2"] = 0
      self.header["y2"] = 0
      #
      self.footer             = {}
      self.footer["exists"]   = False
      self.footer["idxb"]     = 0.0000
      self.footer["idxe"]     = 0.0000
      self.footer["x1"] = 0
      self.footer["y1"] = 0
      self.footer["x2"] = 0
      self.footer["y2"] = 0
      #
      self.text               = ""
      self.text_start_idx     = 0
      self.text_min_d_line    = 0
      self.text_max_d_line    = 0
      self.text_med_d_line    = 0
      self.text_cut_point     = 0 # Should be (self.text_med_d_line * 1.25)
      self.line_factor        = 1.25
      fin = codecs.open(tf.name,"r","UTF-8")
      self.html_code = fin.read()
      fin.close()
      #
      self.soup = BeautifulSoup(self.html_code)
      #
      self.size["width"]  = float(self.soup.find("doc").find("page")["width"])
      self.size["height"] = float(self.soup.find("doc").find("page")["height"])
      #
      self.words = self.soup.find("doc").find("page").findAll("word")
      #
      self.d_dic             = {}
      self.hvet              = []
      self.vvet              = []
      #
      return
   #
   def header_detect(self):
      self.header["x1"] = float(self.words[0]["xmin"])
      self.header["y1"] = float(self.words[0]["ymin"])
      size     = len(self.words)
      i        = 1
      xant     = self.header["x1"]
      yant     = self.header["y1"]
      while (i < (size-1)) and (not self.header["exists"]):
         xtemp = float(self.words[i]["xmin"])
         ytemp = float(self.words[i]["ymin"])
         ydif  = ytemp - yant
         if (ydif > (self.size["height"]/2)):
            self.header["x2"] = float(self.words[i-1]["xmax"])
            self.header["y2"] = float(self.words[i-1]["ymax"])
            self.header["exists"]   = True
         xant = xtemp
         yant = ytemp
         i += 1
      if self.header["exists"]:
         self.header["idxb"] = 0
         self.header["idxe"] = i - 1
      return
   #
   def footer_detect(self):
      if self.header["exists"]:
         self.footer["idxb"] = self.header["idxe"] + 1
      else:
         self.footer["idxb"] = 0
      i        = self.footer["idxb"]
      self.footer["x1"] = float(self.words[i]["xmin"])
      self.footer["y1"] = float(self.words[i]["ymin"])
      size     = len(self.words)
      xant     = self.footer["x1"]
      yant     = self.footer["y1"]
      i += 1
      while (i < (size-1)) and (not self.footer["exists"]):
         xtemp = float(self.words[i]["xmin"])
         ytemp = float(self.words[i]["ymin"])
         ydif  = yant - ytemp
         if (ydif > (self.size["height"]/2)):
            self.footer["x2"] = float(self.words[i-1]["xmax"])
            self.footer["y2"] = float(self.words[i-1]["ymax"])
            self.footer["exists"]   = True
         xant = xtemp
         yant = ytemp
         i += 1
      if self.footer["exists"]:
         self.footer["idxb"] = self.header["idxe"] + 1
         self.footer["idxe"] = i - 1
      return
   #
   def line_space(self):
      if self.footer["exists"]:
         self.text_start_idx = self.footer["idxe"] + 1
      l_botton = []
      min = 9999
      max = 0
      med = 0
      palavras = self.words[self.text_start_idx:]
      for word in palavras:
         y = float(word["ymax"])
         l_botton.append(y)
      #l_botton = sorted(list(set(l_botton)))
      try:
         ant = l_botton[0]
      except:
         if self.debug:
            print("no text in PDF")
         return
      sum = 0
      div = 1
      for y in l_botton[1:]:
          if ant < y:
             dif = y - ant
             if dif > 0:
                sum += dif
                div += 1
                if dif < min:
                   min = dif
                if dif > max:
                   max = dif
             ant = y
      med = sum / div
      self.text_min_d_line    = min
      self.text_max_d_line    = max
      self.text_med_d_line    = med
      self.text_cut_point     = (self.text_med_d_line * self.line_factor)
      if self.debug:
        print(80*"-")
        print("Minimun lines distance: %d" %(self.text_min_d_line))
        print("Maximun lines distance: %d" %(self.text_max_d_line))
        print("Mean lines distance   : %d" %(self.text_med_d_line))
        print("What I call cut point : %d" %(self.text_cut_point))
        print(80*"-")
      return
      #
   def build_text(self):
      if self.footer["exists"]:
         self.text_start_idx = self.footer["idxe"] + 1
      else:
         if self.header["exists"]:
            self.text_start_idx = self.header["idxe"] + 1
      ini = self.text_start_idx

      try:
         yant = float(self.words[ini]["ymax"])
      except:
         self.text = ""
         return(self.text)

      self.text += self.words[ini].text + " "
      palavras = self.words[ini+1:]
      try:
         yant = float(palavras[0]["ymax"])
      except:
         pass
      # --------------------
      idx_word = 0
      n_t_tbl  = len(self.d_dic.keys())
      n_tables = 1
      if n_t_tbl >= n_tables:
         has_table = True
         idx_tbl  = "T"+str(n_tables)
         dim_tbl  = self.d_dic[idx_tbl]["dim"]
         x1_tbl   = dim_tbl[0]
         y1_tbl   = dim_tbl[1]
         x2_tbl   = dim_tbl[2]
         y2_tbl   = dim_tbl[3]
      else:
         has_table = False
      #
      while idx_word < len(palavras):
          #
          word = palavras[idx_word]
          #
          """
          if self.debug:
             print idx_word, word.text
          """
          # ---------------------------
          x1 = float(word["xmin"])
          y1 = float(word["ymin"])
          x2 = float(word["xmax"])
          y2 = float(word["ymax"])
          # ---------------------------
          x_med = (x1+x2)/2
          y_med = (y1+y2)/2
          #
          last_tag = ""
          close_table = False
          #
          if has_table:
             if (x_med > x1_tbl) and (x_med < x2_tbl) and (y_med > y1_tbl) and (y_med < y2_tbl) and (n_tables <= n_t_tbl):
                for r in self.d_dic[idx_tbl]["cells"].keys():
                    n_cols = max(self.d_dic[idx_tbl]["cells"][r].keys())
                    for c in self.d_dic[idx_tbl]["cells"][r].keys():
                       x1_cel = self.d_dic[idx_tbl]["cells"][r][c]["wh"][0]
                       y1_cel = self.d_dic[idx_tbl]["cells"][r][c]["wh"][1]
                       x2_cel = self.d_dic[idx_tbl]["cells"][r][c]["wh"][2]
                       y2_cel = self.d_dic[idx_tbl]["cells"][r][c]["wh"][3]
                       x_cel_m = (x1_cel+x2_cel)/2
                       y_cel_m = (y1_cel+y2_cel)/2
                       if x1 > x1_cel and y_med > y1_cel and y_med < y2_cel:
                          #if "tag" in  self.d_dic[idx_tbl]["cells"][r][c].keys():
                             for i in range(r+1):
                                 for j in range(n_cols+1):
                                    if "tag" in  self.d_dic[idx_tbl]["cells"][i][j].keys():
                                       if (i < r) or ((i == r) and (j <= c)):
                                          last_tag += self.d_dic[idx_tbl]["cells"][i][j]["tag"]
                                          del self.d_dic[idx_tbl]["cells"][i][j]["tag"]
                             #last_tag += self.d_dic[idx_tbl]["cells"][r][c]["tag"]
                             #del self.d_dic[idx_tbl]["cells"][r][c]["tag"]
             #
             still_tags = False
             if (n_tables <= n_t_tbl):
                for r in self.d_dic[idx_tbl]["cells"].keys():
                    for c in self.d_dic[idx_tbl]["cells"][r].keys():
                        if "tag" in self.d_dic[idx_tbl]["cells"][r][c].keys():
                           still_tags = True

             if not still_tags and n_tables <= n_t_tbl:
                close_table = True
                n_tables += 1
                idx_tbl  = "T"+str(n_tables)
                try:
                   dim_tbl  = self.d_dic[idx_tbl]["dim"]
                   x1_tbl   = dim_tbl[0]
                   y1_tbl   = dim_tbl[1]
                   x2_tbl   = dim_tbl[2]
                   y2_tbl   = dim_tbl[3]
                except:
                   pass

          dif = y2 - yant
          if (dif > self.text_cut_point):
             if self.text[-1] == " ":
                self.text = self.text[:-1] + "\n"
             else:
                self.text += "\n"
             #
             if self.file_format == "html":
                self.text += "</br>"
             else:
                self.text += "\n"
          try:
             ultimo_car = word.text[-1]
          except:
             ultimo_car = ""
          #
          if self.file_format == "html":
             my_word = htmlescape(word.text)
          else:
             my_word = word.text
          #
          if (ultimo_car in "-") and (len(word.text) > 1):
             self.text += last_tag + my_word[:-1]
          else:
             try:
               x1_nxt = float(palavras[idx_word+1]["xmin"])
             except:
               x1_nxt = 0
             if (word.text == "N") or (x1_nxt == x2):
                self.text += last_tag + my_word
             else:
                self.text += last_tag + my_word + " "
          #
          if close_table:
            if self.file_format == "html":
               self.text += "</td></tr></table>"
            else:
               self.text += "\n"
            close_table = False
          #
          yant = y2
          #
          idx_word += 1

      if self.file_format == "html":
         #self.text = htmlescape(self.text)
         self.text = "<!DOCTYPE html><html><head><title>Paulo Marques</title></head><body>" + self.text
         self.text = self.text + "</body></html>"
      else:
         self.text = self.text.replace('&quot;','"')

      while "\n\n" in self.text:
         self.text = self.text.replace("\n\n","\n")

      return(self.text)
   #
   def get_hlines(self,pix, w, h, hlin, xscale, ymin, ymax):
       """Get start/end pixels of lines containing horizontal runs of at least THRESH black pix"""
       hlines = []
       for y in range(h):
           if (y > (ymin-10)) and (y < (ymax+10)):
              x = 0
              while x < w:
                 x1 = x
                 x2 = x
                 while (pix[x,y] == (0,0,0)) and (x < (w-1)):
                    x2 = x
                    x += 1
                 if (float((x2 - x1)/xscale) >= hlin):
                    hlines.append([x1,y,x2,y])
                 else:
                    x += 1
       return (hlines)
   #
   def get_vlines(self,pix, w, h, vlin, yscale, ymin, ymax):
       """Get start/end pixels of lines containing horizontal runs of at least THRESH black pix"""
       vlines = []
       for x in range(w):
           #y = 0
           y = ymin-9
           #while y < h:
           while (y < h) and (y > (ymin-10)) and (y < (ymax+10)):
              y1 = y
              y2 = y
              while (pix[x,y] == (0,0,0)) and (y < (h-1)):
                 y2 = y
                 y += 1
              if (float((y2 - y1)/yscale) >= vlin):
                 vlines.append([x,y1,x,y2])
              else:
                 y += 1
       return (vlines)
   #
   def list_to_string(self, v):
      vaux = []
      for i in v:
          txt = ""
          for j in i:
              txt = txt + str(j) + ","
          vaux.append(txt[:-1])
      return vaux
   #
   def get_threshold(self, img_file, thres):
       img = cv2.imread(img_file)
       gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
       edges = cv2.Canny(gray, 370, 730)
       try:
          lines = cv2.HoughLinesP(edges, 1, math.pi, int(thres*10), None, thres, 1);
       except:
          time.sleep(5)
          lines = None
       c_list = []
       if lines is None:
          return(c_list)
       for line in lines[0]:
          x1 = line[0]
          y1 = line[1]
          x2 = line[2]
          y2 = line[3]
          c_list.append([x1,y1,x2,y2])

       y_list = []
       for linha in sorted(c_list):
          for y in range(linha[-1],linha[1]+1):
             y_list.append(y)

       y_list = sorted(list(set(y_list)))

       size = len(y_list)
       old_y = y_list[0]
       y_min = old_y
       idx = 1
       new_y_list = []
       new_y_list.append([y_min])
       while idx < size:
          y  = y_list[idx]
          dif = y - old_y
          while (dif == 1) and (idx < size):
             old_y = y
             y     = y_list[idx]
             dif   = y - old_y
             idx   = idx + 1
          if dif > 1:
             new_y_list[-1].append(y_list[idx - 1])
             old_y = y_list[idx]
             new_y_list.append([old_y])
             idx   = idx + 1

       new_y_list[-1].append(y_list[idx - 1])
       return(new_y_list)
   #
   def tables_detect(self):
      #
      h_line = float(200)
      v_line = float(10)
      #
      tmp_png = NamedTemporaryFile()
      #
      scale = float(1)
      ext = "-png"
      comando = "pdftoppm %s -singlefile -scale-to-x %d -scale-to-y %d %s %s" \
                %(ext,(self.size["width"]*scale),(self.size["height"]*scale),self.filename,tmp_png.name)
      os.system(comando)
      im = Image.open(tmp_png.name+".png")
      width, height = im.size
      #
      x_scale = width/self.size["width"]
      y_scale = height/self.size["height"]
      #
      pixels     = im.load()
      self.thres = self.get_threshold(tmp_png.name+".png", int(self.text_cut_point))
      for y_pts in self.thres:
          y_min = y_pts[0]
          y_max = y_pts[1]
          vh = self.get_hlines(pixels, width, height, h_line, x_scale, y_min, y_max)
          for h in vh:
             self.hvet.append(h)
          vv = self.get_vlines(pixels, width, height, v_line, y_scale, y_min, y_max)
          for v in vv:
             self.vvet.append(v)
      #
      self.hvet = sorted(self.hvet)
      self.vvet = sorted(self.vvet)
      #
      self.d_dic = {}
      n_tables   = 1
      #
      if self.debug:
         print(80*"-")
         print("Horizontal lines vector")
         print self.hvet
         print("Vertical lines vector")
         print self.vvet
         print(80*"-")
      #
      while len(self.vvet) > 0:
         # Find VLINE with less X1, Y1

         i_vline = self.vvet[0]

         # Find TOP HLINE and BOTTON HLINE to VLINE

         x1 = i_vline[0]
         y1 = i_vline[1]
         x2 = i_vline[2]
         y2 = i_vline[3]
         l_temp_h = []

         TOP_LINE = []
         BOT_LINE = []

         for hline in self.hvet:
            if (hline[0] == x1) and (hline[1] == y1):
               TOP_LINE = hline
            if (hline[0] == x1) and (hline[1] == y2):
               BOT_LINE = hline

         # If no horizontal TOP_LINE, but others VLINE in the same Y1, build TOP_LINE
         if len(TOP_LINE) == 0:
            x_temp = x1
            for tline in self.vvet:
                if tline[1] == y1:
                   if tline[0] > x_temp:
                      x_temp = tline[0]
                      TOP_LINE = [x1,y1,x_temp,y1]

         # If no horizontal BOT_LINE, but others VLINE in the same Y2, build BOT_LINE
         if len(BOT_LINE) == 0:
            x_temp = x1
            for tline in self.vvet:
                if tline[3] == y2:
                   if tline[0] > x_temp:
                      x_temp = tline[0]
                      BOT_LINE = [x1,y1,x_temp,y1]

         l_temp_h.append(TOP_LINE)
         l_temp_h.append(BOT_LINE)

         if (l_temp_h[0] == []) or (l_temp_h[1] == []):
            self.vvet.pop(0)
         else:
            i_hline = l_temp_h[0]
            # Find last VLINE to this table
            x1 = i_hline[0]
            y1 = i_hline[1]
            x2 = i_hline[2]
            y2 = i_hline[3]
   
            l_temp_v = []
            for vline in self.vvet:
               if (vline[1] == y1) and ((vline[0] == x1) or (vline[0] == x2)):
                 l_temp_v.append(vline)

            # FIX PIXELS - doing a perfect rectangle
            try:
               l_temp_h[-1][-2] = l_temp_h[-2][-2]
               l_temp_v[-1][-1] = l_temp_v[-2][-1]
            except:
               pass

            # Find all lines inside RECTANGLE (x1,y1,x2,y2)
            x1 = l_temp_h[0][0]
            y1 = l_temp_h[0][1]
            x2 = l_temp_h[-1][-2]
            y2 = l_temp_h[-1][-1]

            for hline in self.hvet:
               if (hline[0] >= x1) and (hline[0] <= x1) and (hline[1] >= y1) and (hline[1] <= y2):
                  if hline not in l_temp_h:
                     l_temp_h.append(hline)
            for vline in self.vvet:
               if (vline[1] >= y1) and (vline[1] <= y2) and (vline[0] >= x1) and (vline[0] <= x2):
                 if vline not in l_temp_v:
                    l_temp_v.append(vline)

            l_temp_h = sorted(l_temp_h)
            l_temp_v = sorted(l_temp_v)

            # Delete from hvet and vvet the lines which were used
            for item in l_temp_h:
               try:
                  self.hvet.pop(self.hvet.index(item))
               except:
                  pass

            for item in l_temp_v:
               try:
                  self.vvet.pop(self.vvet.index(item))
               except:
                  pass

            # This is needed only for my case where right vertical line doesnt touch botton horizontal line
            y1 = l_temp_h[0][1]
            y2 = l_temp_h[-1][3]

            i = 0
            while i < len(l_temp_v):
               l_temp_v[i][1] = y1
               l_temp_v[i][3] = y2
               i += 1

            ltempv   = []
            ltempv   = [item for item in l_temp_v if item not in ltempv]
            l_temp_v = ltempv

            x1 = l_temp_v[0][0]
            x2 = l_temp_v[-1][2]

            i = 0
            while i < len(l_temp_h):
               l_temp_h[i][0] = x1
               l_temp_h[i][2] = x2
               i += 1

            ltemph   = []
            ltemph   = [item for item in l_temp_h if item not in ltemph]
            l_temp_h = ltemph

            # Print Tables
            if self.debug:
               print(80*"-")
               print("Table")
               print("Horizontal Lines")
               print(l_temp_h)
               print("Vertical Lines")
               print(l_temp_v)
               print(80*"-")

            # Vertices detect
            l_vertices = []

            for lth in l_temp_h:
               L1 = line(lth)
               for ltv in l_temp_v:
                  L2 = line(ltv)
                  V = intersection(L1, L2)
                  l_vertices.append(V)

            n_rows = len(l_temp_h)
            n_cols = len(l_temp_v)

            # -----
            cols = get_cols(l_temp_v)
            rows = get_rows(l_temp_h)
            cells = get_cells(rows, cols)
            # -----

            r = 0

            dim_x1 = 9999
            dim_y1 = 9999
            dim_x2 = 0
            dim_y2 = 0

            while r < len(cells.keys()):
                c = 0
                while c < len(cells[r].keys()):
                    item = cells[r][c]
                    cells[r][c] = {}
                    cells[r][c]["wh"]  = item
                    if item[0] < dim_x1:
                       dim_x1 = item[0]
                    if item[1] < dim_y1:
                       dim_y1 = item[1]
                    if item[2] > dim_x2:
                       dim_x2 = item[2]
                    if item[3] > dim_y2:
                       dim_y2 = item[3]
                    if self.file_format == "html":
                       if r == 0 and c == 0:
                          cells[r][c]["tag"] = "<table border=\"1px solid black\" border-collapse=\"collapse\"><tr><td>"
                       else:
                          if c == 0:
                             cells[r][c]["tag"] = "</td></tr><tr><td>"
                          else:
                             cells[r][c]["tag"] = "</td><td>"
                    else:
                       if r == 0 and c == 0:
                          cells[r][c]["tag"] = "\n"
                       else:
                          if c == 0:
                             cells[r][c]["tag"] = "\n"
                          else:
                             cells[r][c]["tag"] = "_||_"
                    c += 1
                r += 1
         
            idx = "T"+str(n_tables)
            self.d_dic[idx] = {}
            self.d_dic[idx]["dim"]   = (dim_x1, dim_y1, dim_x2, dim_y2)
            self.d_dic[idx]["cells"] = cells

            n_tables += 1
      #
      comando = "rm %s" %(tmp_png.name+".png")
      os.system(comando)
      #
      if self.debug:
        for i in range(len(self.d_dic.keys())):
            print("Table %d" %(i+1))
            print(self.d_dic["T"+str(i+1)])
      return         

def get_cols(vlines):
    """Get top-left and bottom-right coordinates for each column from a list of vertical lines"""
    cols = []
    for i in range(1, len(vlines)):
        if vlines[i][0] - vlines[i-1][0] > 1:
            cols.append((vlines[i-1][0],vlines[i-1][1],vlines[i][2],vlines[i][3]))
    return cols
 
def get_rows(hlines):
    """Get top-left and bottom-right coordinates for each row from a list of vertical lines"""
    rows = []
    for i in range(1, len(hlines)):
        if hlines[i][1] - hlines[i-1][3] > 1:
            rows.append((hlines[i-1][0],hlines[i-1][1],hlines[i][2],hlines[i][3]))
    return rows          
 
def get_cells(rows, cols):
    """Get top-left and bottom-right coordinates for each cell usings row and column coordinates"""
    cells = {}
    for i, row in enumerate(rows):
        cells.setdefault(i, {})
        for j, col in enumerate(cols):
            x1 = col[0]
            y1 = row[1]
            x2 = col[2]
            y2 = row[3]
            cells[i][j] = (x1,y1,x2,y2)
    return cells

def convert(_inputfile="", _outputfile="", _debug=False, _tables=False, _format="text"): 
   print("HTML temp...")
   a = PDF_page(_inputfile,_outputfile,_format,_debug)
   year = int(_inputfile.split("/")[-1][:4])
   print("Header detect...")
   a.header_detect()
   print("Footer detect...")
   a.footer_detect()
   print("Counting lines...")
   try:
     a.line_space()
   except:
     pass

   if _tables:
      print("Tables detect...")
      a.tables_detect()

   print("Converting to text...")
   txt = a.build_text()

   fout = codecs.open(a.out_file,"w","utf-8")
   fout.write(txt)
   fout.close()


def main(argv):

   try:
      opts, args = getopt.getopt(argv,"hdti:o:f:",["ifile=","ofile=","format="])
   except getopt.GetoptError:
      print '%s -i <inputfile> -o <outputfile> [-d] [-f [text|html]] [-t]' %(sys.argv[0])
      sys.exit(2)

   _debug      = False
   _tables     = False
   _format     = "text"
   _inputfile  = ""
   _outputfile = ""

   for opt, arg in opts:
      if opt == '-h':
         print '%s -i <inputfile> -o <outputfile> [-d] [-f [text|html]] [-t]' %(sys.argv[0]) 
         sys.exit(0)
      elif opt in ("-i", "--ifile"):
         _inputfile = arg
      elif opt in ("-o", "--ofile"):
         _outputfile = arg
      elif opt in ("-d"):
         _debug = True
      elif opt in ("-f", "--format"):
         _format = arg 
      elif opt in ("-t"):
         _tables = True

   if (_inputfile == "") or (_outputfile == ""):
      print '%s -i <inputfile> -o <outputfile> [-d] [-f [text|html]] [-t]' %(sys.argv[0])
      exit(2)

   print("HTML temp...")
   a = PDF_page(_inputfile,_outputfile,_format,_debug)
   year = int(_inputfile.split("/")[-1][:4])
   print("Header detect...")
   a.header_detect()
   print("Footer detect...")
   a.footer_detect()
   print("Counting lines...")
   a.line_space()

   if _tables:
      print("Tables detect...")
      a.tables_detect()

   print("Converting to text...")
   txt = a.build_text()

   fout = codecs.open(a.out_file,"w","utf-8")
   fout.write(txt)
   fout.close()

if __name__ == '__main__':

   # pdftotext -htmlmeta -bbox -raw PDF_FILE.pdf
   # pdftoppm -png -singlefile -scale-to-x WIDTH -scale-to-y HEIGHT PDF_FILE.pdf 
   main(sys.argv[1:])

