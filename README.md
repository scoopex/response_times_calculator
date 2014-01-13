response_times_calculator
=========================

Calculate website performance statistics based on apache logfiles

# Install


Software prerequisites:
 * python


# Apache configuration

Define the following logformattter and use it in the virtual host
```
LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %D" combined_performance
CustomLog "logs/access_log" combined_performance
```


# Tomcat configuration


``` 
<Host name="localhost"  appBase="webapps"
            unpackWARs="true" autoDeploy="true"
             xmlValidation="false" xmlNamespaceAware="false">
...
<Valve className="org.apache.catalina.valves.FastCommonAccessLogValve" directory="logs"  
               prefix="access." suffix=".log" pattern="%h %l %u %t &quot;%r&quot; %s %b %I %S %D"/>
...
```


# Usage

Invoke "response_times_calculator.py" on compressed and uncompressed apache logfiles

```
./response_times_calculator.py -c default.cfg -r access_log.gz access_log
```

# Licence and Authors

Additional authors are very welcome - just submit your patches as pull requests.

 * Marc Schoechlin <ms@256bit.org>
 * Marc Schoechlin <marc.schoechlin@dmc.de>


