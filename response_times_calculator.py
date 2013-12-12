#!/usr/bin/env python

#########################################################
###
### Marc Schoechlin [ms@256bit.org]
###

import glob,sys,re,os,getopt,time,signal,gzip,ConfigParser
from pprint import pprint


## This function processes one logfile with regexes and stores
## the results in the global hash "dashboard"

def readAccessLog(file):

  # open file
  print "reading from '%s'" % file
  if file == "-":
       accesslog = sys.stdin
  elif file.upper().endswith(".gz".upper()):
       accesslog = gzip.open(file, 'rb')
  else:
       accesslog = open(file, 'r')

  count =  0
  skipped = 0
  unmatched = 0

  service_classes_tmpl = {}
  for i in service_classes:
     service_classes_tmpl[i] = 0
  
  if (include_match != None):
    re_includematch = re.compile(include_match)

  while 1:
    lineStr = accesslog.readline().rstrip()

    if (include_match != None) and not re_includematch.match(lineStr):
        if "debug" in flags: print "[skip, does not match] " + lineStr
        skipped += 1
        continue
        
    # end of file
    if not(lineStr):
        break
    count += 1
    if (count % 1000000 == 0):
        print "%i lines read...%s" % (count,file)
    lineElements = re_parselogs.match(lineStr)
    if (not lineElements):
       print "INFO: line does to match (global/line_regex): %s" % lineStr
       continue

    if not re_http_status_code_regex.match(lineElements.group("code")):
       if "debug" in flags: print "[skip, wrong http status code] " + lineStr
       skipped += 1
       continue

    hashmatched = 0
    for value in dashboard.itervalues():
      urlmatch = value["regex"].match(lineElements.group("url"))

      if value["negate"] == True:
      	if urlmatch :
            continue
        ident_string = "negate"
      else: 
      	if not urlmatch :
            continue
        ident_string = urlmatch.group("ident")

      hashmatched += 1

      value["count"] += 1
      value.setdefault("matches",{})

      value["matches"].setdefault(ident_string,0)
      value["matches"][ident_string] += 1

      value.setdefault("exectime",{})
      exectime = int(lineElements.group("exectime"))
      value["exectime"].setdefault(ident_string,0)
      value["exectime"][ident_string] += exectime 

      value.setdefault("classes",{})
      value["classes"].setdefault(ident_string,service_classes_tmpl.copy())


      value["stats"].setdefault("exectime",0)
      value["stats"]["exectime"] += exectime
      
      iter = -1 
      for cclass in service_classes:
         iter += 1
         # The infinity service class
         if (cclass == "-1"):
           break
         elif int(exectime) < int(cclass):
           break
      
      value["classes"][ident_string][service_classes[iter]] += 1

    if (hashmatched == 0):
       unmatched += 1
       if "debug" in flags: print "[line not matched by any group] " + lineStr
  accesslog.close()
  return (count,skipped,unmatched)

# This method calculates statistics after all logfiles were processed
#
def createStats():

  print "\n** creating statistics\n"

  # Assemble the header data
  arr_header = [ "category name","match","count","average response time per hit (1/1000000 seconds)" ]

  last = 0
  for i in service_classes:
    if (i == "-1"):
        arr_header.append("> "+ str(last) + " (1/1000000 seconds)")
    else:
        arr_header.append((str(last) + "-" + str(i))+" (1/1000000 seconds)")
    last = i

  dict_data = {}

  # Assemble data of the total stats
  for catname,catdata in dashboard.iteritems():
    # Write total stats
    stats = catdata["stats"]
    if catdata["count"] > 0:
        avg_exec = "%f" % (stats["exectime"] / catdata["count"])
    else:
        avg_exec = "0"
    dataset = [str(catdata["count"]),avg_exec]

    for service_class in service_classes:
        totalcount = 0
        if (catdata.has_key("classes")):
            for classname,classdata in catdata["classes"].iteritems():
                totalcount += classdata[service_class]
        dataset.append(str(totalcount))

    dict_data.setdefault(catname, {})
    dict_data[catname]["total"] = dataset

    
  # pprint(dashboard)

  # Assemble data of the detail stats
  for catname,catdata in dashboard.iteritems():
    if (catdata.has_key("classes")):
        for classname,classdata in catdata["classes"].iteritems():
            dict_data[catname][classname] = []
            dict_data[catname][classname].append(str(catdata["matches"][classname]))
            avg_exec = "%f" % ( catdata["exectime"][classname] / catdata["matches"][classname] )
            dict_data[catname][classname].append(avg_exec)

            for service_class in service_classes:
                dict_data[catname][classname].append(str(classdata[service_class]))

  return (arr_header,dict_data)

# This method creates human readable results
def outputStatsReadable(arr_header,dict_data):

  for catname,catdata in sorted(dict_data.iteritems()):
    print "\n===> Category %s <===========================================================================" % catname
    print
    outarr = [i for i in sorted(catdata) if (i != "total")]
    outarr.insert(0,"total")

    maxlen=0
    for i in arr_header:
        if (maxlen < len(i)):
            maxlen=len(i)

    format_string = "  %-"+str(maxlen)+"s => %s"
    for matchname in outarr:
       if matchname == "":
            continue
       print "\n[%s]" % matchname
       for i_header in range(2,len(arr_header)):
            if (i_header == 4):
                print
            print format_string % (arr_header[i_header],catdata[matchname][i_header-2])

# This method creates a comma separated result file which can be used in libreoffice of excel
def outputStatsCSV(arr_header,dict_data):
  fout = file(outputfile_csv, "w")
  fout.write("#" + ";".join(arr_header)+";\n")
  for catname,catdata in sorted(dict_data.iteritems()):
    out = "%s;%s;" % (catname,"total") + ";".join(catdata["total"])+";\n"
    fout.write(out.replace(".",","))
    for matchname,dataset in sorted(catdata.iteritems()):
        if ( matchname == "total"):
            continue
        out = "%s;%s;" % (catname,matchname) + ";".join(dataset)+";\n"
        fout.write(out.replace(".",","))

  fout.close()

# This method creates a javascript results file
def outputStatsJavascript(arr_header,dict_data):
  fout = file(outputfile_js, "w")
  fout.write('var data = [\n')
  count=1
  for header in arr_header:
    fout.write("    // Column %i : %s\n" % (count,header));
    count +=1

  formatstring_front = '    [%-20s, %-20s, %-20s'
  formatstring_back = ', %12s'

  for catname,catdata in sorted(dict_data.iteritems()):
    fout.write(formatstring_front % ('"'+outputfile_js+'"','"'+catname+'"','"total"'))
    for i in catdata["total"]:
        fout.write(formatstring_back % i)
    fout.write("],\n");
    for matchname,dataset in sorted(catdata.iteritems()):
        if ( matchname == "total"):
            continue
        fout.write(formatstring_front % ('"'+outputfile_js+'"','"'+catname+'"','"'+matchname+'"'))
        for i in catdata[matchname]:
            fout.write(formatstring_back % i)
        fout.write("],\n");

  fout.write(']\n')
  fout.close()


####################################################################
###
### Helpers

def usage():
  print sys.argv[0]+" [options] file..."
  print '''
 -h  view this help message
 -c  configfile
 -d  debug
 -m  regex, only parse matching lines
 -o  output a comma seperated file (csv - suitable spreadsheet calculators)
 -j  output a javascript array
 -r  output in readable format to stdout
'''
  sys.exit(1)

##################################################################
###
### MAIN

if len(sys.argv) < 2:
  usage()

flags = []
## evaluate the commandline arguments
try:
    opt, argv = getopt.getopt(sys.argv[1:], "hdo:c:m:j:r")
except:
    print "Error parsing commandline arguments"
    usage()
    sys.exit(1)

cfgfile = None 
include_match = None

for o, a in opt:
    if a.startswith("-"):
      usage()
      sys.exit(1)
    if o == "-h":
      usage()
      sys.exit(1)
    elif o == "-d":
      flags.append("debug")
    elif o == "-o":
      flags.append("output")
      outputfile_csv = a
    elif o == "-j":
      flags.append("javascript")
      outputfile_js = a
    elif o == "-r":
      flags.append("readable")
    elif o == "-c":
      cfgfile = a
    elif o == "-m":
      include_match = a
    else:
      usage()
      sys.exit(1)

if (len(argv) == 0):
   usage()
   sys.exit(1)

if ("output" not in flags) and ("javascript" not in flags) and ("readable" not in flags):
    print "No output defined, exiting"
    sys.exit(1)

if ("output" in flags) and (outputfile_csv == None):
   print "csv outputfile not defined, exiting"
   sys.exit(1)

if ("javascript" in flags) and (outputfile_js == None):
   print "javascript outputfile not defined, exiting"
   sys.exit(1)

print "** reading configuration"
if (cfgfile == None):
  print "error: undefined configfile"
  print
  usage()

# get configuration
cfg = ConfigParser.ConfigParser()
cfg.readfp(open(cfgfile, "r"))


if cfg.has_section("global") and cfg.has_option("global","line_regex"):
  match = re.match("^.*?'(.+)'.*?$",cfg.get("global","line_regex"))
  if match:
     print "line parsing string : '%s'" % match.group(1)
     re_parselogs = re.compile(match.group(1))
  else:
     print "error: please quote the line_regex string"
     sys.exit(1)
else:
  print "missing key 'line_regex' in section 'global'"
  sys.exit(1)

if cfg.has_section("global") and cfg.has_option("global","service_classes"):
  service_classes = re.compile(r'\s*,\s*').split(cfg.get("global","service_classes"))
  service_classes = [int(a) for a in service_classes]
  service_classes.sort()
  # The infinity service class
  service_classes.append("-1")
  print "service classes     : %s " % str(service_classes)
else:
  print "missing key 'service_classes' in section 'global'"
  sys.exit(1)

if cfg.has_section("global") and cfg.has_option("global","http_status_code_regex"):
  match = re.match("^.*?'(.+)'.*?$",cfg.get("global","http_status_code_regex"))
  if match:
     print "matched status code string : '%s'" % match.group(1)
     re_http_status_code_regex = re.compile(match.group(1))
  else:
     print "error: please quote the http_status_code_regex string"
     sys.exit(1)


# request types
dashboard = {}
for sect in cfg.sections():
  if sect == "global":
     continue
  print "=> section '%s'" % sect
  if cfg.has_option(sect,"url_regex"):
     match = re.match("^.*?'(.+)'.*?$",cfg.get(sect,"url_regex"))
     if match:
        print "  url parsing string: '%s'" % match.group(1)

        dashboard[sect] = {}
        try:
           dashboard[sect]["regex"] = re.compile(match.group(1))
        except:
           print "regex '%s' seems to be broken, unable to compile" % match.group(1)
        dashboard[sect]["regex_uncompiled"] = match.group(1)
        dashboard[sect]["count"] = 0
        dashboard[sect]["stats"] = { "exectime" : 0 }
        if cfg.has_option(sect,"negate") and cfg.get(sect,"negate") == "true":
           dashboard[sect]["negate"] = True
        else:
           dashboard[sect]["negate"] = False
     else:
        print "error: please quote the url_regex string"
        sys.exit(1)
  else:
     print "missing key: url_regex"
     sys.exit(1)
  

# start processing the files
starttime = time.time()
lines = 0
skipped = 0
umlines = 0

print "\n** processing files"
# read the logfiles

processed_files=0
total_files=len(argv)
for access_log in argv:
  try:
   tlines,skipped,unmatchedlines = readAccessLog(access_log)
   currenttime = time.time()
   processed_files += 1
   if ( processed_files != 0 ):
     time_perfile = (currenttime - starttime) / processed_files
     remaining_time = (total_files - processed_files) * time_perfile
     print "%i of %i files processed (%d seconds per file, remaining time %d hours)" % (processed_files,total_files, time_perfile, remaining_time/60/60)
   lines += tlines
   skipped += skipped
   umlines += unmatchedlines
  except KeyboardInterrupt:
        print "\nWARNING => file processing interupted\n"
        break

endtime = time.time()
# processing finished, print stats
print "processed %d lines in %s seconds (%d lines per second)" % (
    lines,(endtime-starttime),lines/(endtime-starttime)
    )
print "%s unmatched lines" % umlines
print "%s skipped lines" % skipped

(arr_header,dict_data) = createStats()

if ("output" in flags):
    outputStatsCSV(arr_header,dict_data)

if ("javascript" in flags):
    outputStatsJavascript(arr_header,dict_data)

if ("readable" in flags):
    outputStatsReadable(arr_header,dict_data)

# vim: ai et ts=2 shiftwidth=2
