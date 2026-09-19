<h1>Apple Script to automate Garmin Upload</h1>
<p>The app will run and constantly check (every 30 seconds) whether MyWhoosh is running. Once started, it will listen to My Whoosh being quit/exited. In case My Whoosh was exited/quit, it will run the myWhoosh2Garmin.py script that needs to be installed and setup previously.</p>
<h2>🛠️ Installation Steps:</h2>
<ol>
  <li>Download MyWhoosh2Garmin-AS.scpt to your filesystem to a folder of your choosing.</li>
  <li>Go to the folder where you downloaded the script via Mac Finder.</li>
  <li>Open the script in the Apple Script Editor and set the property <code>pythonScriptPath</code> to the location where you downloaded the 
  <code>myWhoosh2Garmin.py</code> script. <code>do shell script</code> runs with a minimal PATH, so <code>uv</code>
  is called by its full path below; adjust it if <code>which uv</code> reports a different location.</li>
  
```
property targetApp : "MyWhoosh Indoor Cycling App"
property pythonScriptPath : "/path/to/myWhoosh2Garmin.py"
property appRunning : false

on idle
	if application targetApp is running then
		set appRunning to true
	else if appRunning then
		set appRunning to false
		performActionOnExit()
	end if
	return 30 -- Check every 30 seconds
end idle

on performActionOnExit()
	do shell script "$HOME/.local/bin/uv run " & quoted form of pythonScriptPath
end performActionOnExit

on quit
	continue quit
end quit

```

  <li>After changing the property file, export the file as an app.</li>
  <li>Please select File Format <code>Application</code>.</li>
  <li>Please select <code>Stay open after run handler</code> an export option.</li>
  <li>Store the app at a location of your choice.
	<img width="1100" alt="Xnip2024-12-30_22-16-55" src="https://github.com/user-attachments/assets/54fa1ab0-2ed3-46a0-808e-1420c29c7736" />
  </li>
  <li>Before running the script, you need to grant the app full access to your hard drive. Otherwise, you will be prompted each time to allow access when the myWhoosh2Garmin is executed. Please search the web for a guide, given it slightly depends on your Mac OS version. See screenshot of my setup (I gave my App the My Whoosh icon): <img width="827" alt="Xnip2024-12-30_22-28-22" src="https://github.com/user-attachments/assets/c4004375-36ef-42c1-936f-99eba47639c6" />
  </li>
  <li>Now you can run the App and start riding on My Whoosh. After you exit My Whoosh the Garmin upload script will be exectuded.</li>
</ol>
