<h1 align="center" id="title">myWhoosh2Garmin</h1>

<h2>🧐Features</h2>

*   Downloads your rides from the MyWhoosh cloud, the same .fit files the MyWhoosh website offers under ACTIVITY FILES. It works whichever device you rode on.
*   Catches up: of your MyWhoosh rides from the last 14 days (up to the 10 most recent), it uploads every one that Garmin Connect does not have yet. A ride counts as already there when a Garmin activity starts at the same time, so rides uploaded by hand or by an older version of this script are not uploaded twice.
*   With `--local`, reads the most recent export from the MyWhoosh app folder instead, .fit or .gpx. A .gpx export is converted into a .fit file when it is the newer of the two: MyWhoosh 6.2.0 wrote MyNewActivity-&lt;version&gt;.gpx for one ride and MyNewActivity-&lt;version&gt;.fit for the next, so both can sit in the folder at once and the older one must not win.
*   Fix the missing power & heart rate averages. MyWhoosh 6.2.0 fills these in itself, in which case they are left as they are.
*   Removes the temperature.
*   Create a backup file to a folder you select.
*   Uploads the fixed .fit file to Garmin Connect.

<h2>🛠️ Installation Steps:</h2>

<p>1. Install <code>uv</code> (if not already installed):</p>

- <b>MacOS / Linux:</b>

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- <b>Windows</b> (PowerShell):

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

<p>2. Download myWhoosh2Garmin.py to your filesystem to a folder or your choosing.</p>

<p>3. Go to the folder where you downloaded the script in a shell.</p>

- <b>MacOS:</b> Terminal of your choice. 
- <b>Windows:</b> Start > Run > cmd or Start > Run > powershell

<p>4. Put your MyWhoosh credentials in a file named <code>.env</code> next to the script:</p>

```
MYWHOOSH_EMAIL=you@example.com
MYWHOOSH_PASSWORD=your-mywhoosh-password
```

`.env` is in `.gitignore`, so it stays out of the repository. Keep it private, for example with `chmod 600 .env`. Environment variables of the same name take precedence over the file. Only the MyWhoosh password goes here: Garmin Connect is authenticated once interactively, and its session is kept in `.garth/`.

<p>5. Run the script:</p>

```
uv run myWhoosh2Garmin.py
```

The dependencies and the required Python version are declared at the top of the script itself, so `uv` fetches Python 3.13 and the dependencies (`garth`, `fit_tool`, `requests`, `python-dotenv`) into a cached environment on the first run. There is no virtual environment to create or activate.

Exact versions are pinned in `myWhoosh2Garmin.py.lock`, which `uv run` picks up automatically. Two optional extras:

```
uv sync --script myWhoosh2Garmin.py   # install everything up front instead of on first run
uv run --locked myWhoosh2Garmin.py    # fail instead of re-resolving if the lock is stale
```
  
<p>6. Choose your backup folder.</p>

<h3>MacOS</h3>

![image](https://github.com/user-attachments/assets/2c6c1072-bacf-4f0c-8861-78f62bf51648)


<h3>Windows</h3>


![image](https://github.com/user-attachments/assets/d1540291-4e6d-488e-9dcf-8d7b68651103)

<p>7. Enter your Garmin Connect credentials</p>

```
2024-11-21 10:08:04,014 No existing session. Please log in.
Username: <YOUR_EMAIL>
Password:
2024-11-21 10:08:33,545 Authenticating...

2024-11-21 10:08:37,107 Successfully authenticated!
```

<p>8. Run the script when you're done riding, after quitting MyWhoosh.</p>

MyWhoosh allows one session per account, so the download is refused while the app is running:

```
MyWhoosh login failed: You are already logged in from another device.
Quit the MyWhoosh app and run again.
```

A successful run looks like this:

```
2026-09-23 09:04:40,455 Authenticated to MyWhoosh.
2026-09-23 09:04:46,378 Already on Garmin Connect: MyWhoosh - Base (2026-09-20T13:12:50.000Z).
2026-09-23 09:04:46,378 New MyWhoosh activity: MyWhoosh - Arctic Trail (2026-09-23T06:32:48.000Z).
2026-09-23 09:04:46,920 Cleaned-up file saved as <YOUR_BACKUP_FOLDER>/MyWhoosh_2026-09-23_083248.fit
```

Each backup is named after the ride's start time. Running the script again uploads nothing new, since every ride it finds is then already on Garmin Connect.

To use the app folder instead of the cloud (newest export only, no catch-up):

```
uv run myWhoosh2Garmin.py --local
```

<p>(9. Or see below to automate the process)</p>

<h2>ℹ️ Automation tips</h2> 

What if you want to automate the whole process:
<h3>MacOS</h3>

PowerShell on MacOS (Verified & works)

You need Powershell

```shell
brew install powershell/tap/powershell
```

```powershell
# Define the JSON config file path
$configFile = "$PSScriptRoot\mywhoosh_config.json"
$myWhooshApp = "myWhoosh Indoor Cycling App.app"

# Check if the JSON file exists and read the stored path
if (Test-Path $configFile) {
    $config = Get-Content -Path $configFile | ConvertFrom-Json
    $mywhooshPath = $config.path
} else {
    $mywhooshPath = $null
}

# Validate the stored path
if (-not $mywhooshPath -or -not (Test-Path $mywhooshPath)) {
    Write-Host "Searching for $myWhooshApp"
    $mywhooshPath = Get-ChildItem -Path "/Applications" -Filter $myWhooshApp -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1

    if (-not $mywhooshPath) {
        Write-Host " not found!"
        exit 1
    }

    $mywhooshPath = $mywhooshPath.FullName

    # Store the path in the JSON file
    $config = @{ path = $mywhooshPath }
    $config | ConvertTo-Json | Set-Content -Path $configFile
}

Write-Host "Found $myWhooshApp at $mywhooshPath"

Start-Process -FilePath $mywhooshPath

# Wait for the application to finish
Write-Host "Waiting for $myWhooshApp to finish..."
while ($process = ps -ax | grep -i $myWhooshApp | grep -v "grep") {
    Write-Output $process
    Start-Sleep -Seconds 5
}

# Run the Python script
Write-Host "$myWhooshApp has finished, running Python script..."
uv run "<PATH_WHERE_YOUR_SCRIPT_IS_LOCATED>/MyWhoosh2Garmin/myWhoosh2Garmin.py"
```

AppleScript (need to test further)

```applescript
TODO: needs more work
```

<h3>Windows</h3>

Windows .ps1 (PowerShell) file (Untested on Windows)
```powershell
# Define the JSON config file path
$configFile = "$PSScriptRoot\mywhoosh_config.json"

# Check if the JSON file exists and read the stored path
if (Test-Path $configFile) {
    $config = Get-Content -Path $configFile | ConvertFrom-Json
    $mywhooshPath = $config.path
} else {
    $mywhooshPath = $null
}

# Validate the stored path
if (-not $mywhooshPath -or -not (Test-Path $mywhooshPath)) {
    Write-Host "Searching for mywhoosh.exe..."
    $mywhooshPath = Get-ChildItem -Path "C:\PROGRAM FILES" -Filter "mywhoosh.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1

    if (-not $mywhooshPath) {
        Write-Host "mywhoosh.exe not found!"
        exit 1
    }

    $mywhooshPath = $mywhooshPath.FullName

    # Store the path in the JSON file
    $config = @{ path = $mywhooshPath }
    $config | ConvertTo-Json | Set-Content -Path $configFile
}

Write-Host "Found mywhoosh.exe at $mywhooshPath"

# Start mywhoosh.exe
Start-Process -FilePath $mywhooshPath

# Wait for the application to finish
Write-Host "Waiting for mywhoosh to finish..."
while (Get-Process -Name "mywhoosh" -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 5
}

# Run the Python script
Write-Host "mywhoosh has finished, running Python script..."
uv run "C:\Path\to\myWhoosh2Garmin.py"
```

<h2>💻 Built with</h2>

Technologies used in the project:

* Neovim
*   <a href="https://github.com/matin/garth">Garth</a>
*   <a href="https://github.com/marcelorodrigo/mywhoosh-to-garmin">mywhoosh-to-garmin</a>, for the MyWhoosh cloud API endpoints
*   tKinter
*   <a href="https://bitbucket.org/stagescycling/fit_tool/src/main/">Fit\_tool</a>
