# Operations Manual — Delivery Intelligence Platform (DIP)

For the owner and dispatcher of Chicago Cargo Couriers. Covers running the
platform day to day, accounts, the dispatch workflow, and what to do when
something fails. Drivers get the one-page [Driver Guide](DRIVER_GUIDE.md).

*Last updated 2026-10-11. Replaces the dispatcher and mobile parts of
`docs/USER_GUIDE.md` and the July `Delivery_Intelligence_Platform_Operational_Manual.md.pdf`.*

---

## 1. What runs where

| Part | Where | Address |
|---|---|---|
| Backend + database + Redis | Docker on the office PC | API `http://localhost:8000` |
| **Dispatch dashboard** | Docker on the office PC | **http://localhost:5173** |
| **Driver app** | Each driver's phone (Expo Go for now) | connects to the office PC over Wi-Fi |
| Proof photos | Office PC disk (`src/uploads/proofs`), backed up every hour | Cloudflare R2 in production |

The phones reach the office PC over the **same Wi-Fi network**, or from
anywhere once public access is switched on (section 10).

## 2. Start and stop

Open PowerShell in `C:\Projects\DELIVERYINTELLIGENCEPLATFORM`.

| Task | Command |
|---|---|
| **Start** (also applies updates and database migrations) | `.\scripts\dev\start.ps1` |
| **Stop** (data is kept) | `.\scripts\dev\stop.ps1` |
| Is it running? | `docker compose ps` and open http://localhost:8000/health (shows `"ok"`) |
| Start the driver app server for phones | `cd src\mobile; npm run go` (leave the window open) |

Docker Desktop must be running first. Never use `start.ps1 -Reset` or
`stop.ps1 -Wipe` unless you mean to **delete all data**. Never use
`start.ps1 -Seed` on the real database: it adds 50 fake drivers.

## 3. Accounts and passwords

Roles: **driver** (phone app), **dispatcher** (dashboard: jobs, drivers,
packages, proofs), **manager**, **admin**.

| Task | Command (PowerShell, stack running) |
|---|---|
| Create an account | `docker exec -it delivery_backend python -m src.scripts.create_user <username> <driver\|dispatcher\|manager\|admin>` |
| Reset a password | `docker exec -it delivery_backend python -m src.scripts.set_user_password <username>` |
| Lock someone out | Reset their password to one only you know (there is no "disable" button yet) |

- Both commands ask for the password and **don't show it**. Minimum 10 characters.
- A driver's **username is their driver ID**. New drivers appear in "Assign Driver" right away.
- Give each driver their own account. Never share one.
- **`.env` holds the `SECRET_KEY` that signs every login.** Keep it private and never commit it. If it's missing, `start.ps1` stops with *"SECRET_KEY must be set in .env"*. Changing it logs everyone out; that's harmless.
- Keep account recovery codes (Expo, GitHub, …) in a password manager, not in the project folder.

## 4. Set up a driver's phone

1. Install **Expo Go** from the App Store / Google Play.
2. Make sure the phone is on the **office Wi-Fi**.
3. On the office PC, run `npm run go` in `src\mobile`. If the PC's IP address changed, first run `.\scripts\dev\configure-mobile-env.ps1`.
4. Open Expo Go on the phone, choose the office PC under *Development servers* (or *Enter URL manually*: `exp://<office-PC-IP>:8081`), and log in with the driver's account.
5. Allow **Location**, **Camera** and **Notifications**.
6. Give the driver the [Driver Guide](DRIVER_GUIDE.md).

## 5. The daily dispatch flow

### Create a job (dashboard → **Scheduling** → *Create Job*)

1. Choose the **Type**, then a title, priority and scheduled time:
   - **Delivery**: the pickup address is optional (leave it blank if the package starts in the van).
   - **Pickup**: you're collecting from a shipper. The pickup address is required, and **Deliver to** is where it goes (the customer, or your depot).
2. **Pickup address** (optional), if the driver collects the package first:
   - Watch the **Matched:** line. **Orange** means Chicago was assumed; add the city for suburbs.
   - Add **pickup instructions** (who to ask, which door).
   - Untick **Ready for pickup now** if the shipper isn't ready yet.
3. **Delivery address** (required): check its **Matched:** line too. Street and number is enough in Chicago.
4. **Suite / floor / dock**, **Delivery instructions** and **Recipient name / phone**, plus **Pickup contact / phone** for a pickup. **These are what the driver sees**; the driver can tap to call. "Internal notes" are **not** shown to the driver.
5. **Assign Driver**, now or later. The driver's phone gets an alert as soon as the job is assigned.

Each package gets a tracking code like **CCC-7K3QX9M2**. It's on the
Packages page; the driver can scan it as a barcode or QR code.

### During the day (dashboard → **Packages**)

- **Not ready for pickup** → when the shipper calls, click **Mark ready**. The driver is alerted.
- **Problem reported** → a **red alert** pops up on the dashboard with the driver's reason. Call the driver or customer, then either:
  - **Reopen**: it goes back on the driver's list. If it was already picked up, it stays "in the van"; or
  - create a new job (for example to return it to the shipper).
- **Proof Gallery** → photo, signature, **who received it**, time and GPS distance for every delivery. Use it when a customer asks for proof.

### Package statuses

| Status | Meaning |
|---|---|
| pending | Created, no driver |
| assigned | Driver has it on their list (pickup stage, if it has a pickup address) |
| picked up (loaded) | In the van |
| delivered | Done, with proof |
| problem (exception) | Driver couldn't complete it; reason shown |

## 6. When something fails

| Symptom | Likely cause | Fix |
|---|---|---|
| Dashboard won't load | Stack not running | Start Docker Desktop, then `.\scripts\dev\start.ps1` |
| Everyone is logged out | `SECRET_KEY` changed, or session expired | Log in again |
| "Incorrect username or password" | Wrong or forgotten password | `set_user_password` (section 3) |
| Phone: network error / can't log in | Phone not on office Wi-Fi, PC IP changed, or `npm run go` not running | Check Wi-Fi; run `configure-mobile-env.ps1`; restart `npm run go` |
| Driver not in "Assign Driver" | Account isn't a driver, or doesn't exist | Create with `create_user … driver` |
| "Address not found" | Typo or missing city | Add city, state or ZIP; check the Matched line |
| Driver gets no alerts | Notifications not allowed, or app closed | Allow notifications; keep the app open (it checks every 30 s). Background push needs the production app on Android |
| Proof shows "No GPS" | Location off or blocked | Phone Settings → Expo Go → Location → *While Using* |
| Delivery "Saved Offline" | No signal at the door | Nothing to do; it sends when the phone is back online |
| Address lookups fail for everyone | US Census geocoder is down (rare) | Wait and retry; it's a free government service |
| Start stops with "SECRET_KEY must be set" | `.env` missing the key | Add a `SECRET_KEY=` line (see `.env.example`) |

To look deeper: `docker compose logs backend --tail 100`.

## 7. Backups (automatic)

Every night at **23:00** (or as soon as the PC is back on), the **DIP Nightly
Backup** task runs `scripts\ops\backup.ps1`. It:

1. Dumps the database (jobs, packages, proofs, accounts) and checks that the dump can be read back.
2. Keeps **7 daily and 4 weekly** dumps in `C:\DIP-Backups\db`.
3. Copies new proof photos to `C:\DIP-Backups\proofs`. Photos are never deleted from the backup.
4. Copies everything **off this PC** to `OneDrive\DIP-Backups`, which syncs to Microsoft's cloud. Use your **business** OneDrive account: the backups contain customer photos and addresses.

The **DIP Photo Backup** task runs **every hour** and copies new proof photos
to `C:\DIP-Backups\proofs` and `OneDrive\DIP-Backups\proofs`, so a photo
taken in the afternoon is not waiting for the nightly run. It takes seconds
and writes a line to `C:\DIP-Backups\photos.log` only when it copied
something (or failed).

The **DIP Backup Check** task runs at logon and at 09:00 and **pops up a
warning** if the last good backup is more than 26 hours old.

Old fleet-simulator test photos (30,932 files) were moved out of DIP on
2026-10-12 to `C:\DIP-Archive\simulator-proofs-2026-10-12`. They are test
data, not deliveries, and can be deleted whenever you like.

| Task | Command (PowerShell in the project folder) |
|---|---|
| Install or change the schedule (**as administrator**) | `.\scripts\ops\install-backup-tasks.ps1 -OffsiteDir "$env:OneDrive\DIP-Backups"` |
| Back up now | `.\scripts\ops\backup.ps1 -OffsiteDir "$env:OneDrive\DIP-Backups"` |
| Is the last backup recent? | `.\scripts\ops\check-backup.ps1` |
| Copy new photos now | `.\scripts\ops\backup-photos.ps1 -OffsiteDir "$env:OneDrive\DIP-Backups"` |
| What happened? | open `C:\DIP-Backups\backup.log` (photos: `photos.log`) |
| **Prove a backup restores** (monthly) | `.\scripts\ops\test-restore.ps1` |

`test-restore.ps1` restores the newest dump into a separate scratch database,
compares row counts with the live data, prints the time taken and deletes the
scratch database. It never touches live data. **Last test: 2026-10-11, 1.0 s,
all tables matched.**

Docker Desktop must be running for the nightly backup. If the PC was off,
the task runs when it next starts, and the 09:00 check tells you if it was missed.

**Restore for real** (replaces the current database; stop work first):

```powershell
docker compose stop backend telemetry_worker
docker cp C:\DIP-Backups\db\daily\dip-db-YYYYMMDD-HHMMSS.dump delivery_db:/tmp/restore.dump
docker exec delivery_db pg_restore -U postgres -d delivery --clean --if-exists /tmp/restore.dump
.\scripts\dev\start.ps1
```

If this PC is lost, install DIP on a new PC, copy `OneDrive\DIP-Backups` to
`C:\DIP-Backups`, start it once, run the restore above, and copy the
`proofs` folder back to `src\uploads\proofs`.

## 8. Updating the software

```powershell
git pull
.\scripts\dev\start.ps1      # rebuilds, applies database migrations, restarts
```

Then restart `npm run go` for the phones and reload the app (shake the phone → *Reload*).

## 9. Known limits (being worked on)

- Drivers use **Expo Go** in development mode; a store-installed app comes later (Phase 8).
- Off the office Wi-Fi only after public access is set up (section 10), and only while the office PC is on.
- **Tracking** shows positions only when drivers confirm or check location, not continuous live tracking.
- Route optimisation isn't connected to the driver's list; stops are listed pickups first.
- No printed labels yet. Copy the CCC- tracking code from Packages if you need one.

## 10. Going online (Cloudflare Tunnel)

DIP stays on the office PC, but a **Cloudflare Tunnel** makes it reachable
from anywhere at `https://dip.<yourdomain>`: the dashboard from any browser,
and the driver app on mobile data. No router ports are opened. The PC
connects *out* to Cloudflare, which adds HTTPS. API docs and metrics stay
blocked from the internet.

### One-time setup in Cloudflare (owner)

1. **Create a free Cloudflare account** at https://dash.cloudflare.com/sign-up.
2. **Add your domain** (*Add a site*, Free plan). Cloudflare copies your existing DNS records. **Check that your email (MX) records and website records are in the list** before going on, or email can stop working.
3. **At your registrar** (where you bought the domain), replace the nameservers with the two Cloudflare shows you. Wait until Cloudflare says the domain is **Active**. That's usually under an hour, but can take up to a day.
4. In **Zero Trust** (https://one.dash.cloudflare.com): **Networks → Tunnels → Create a tunnel → Cloudflared**, name it `dip-office`, choose **Docker**, and **copy the token**: the long text after `--token` in the command shown. Treat it like a password.
5. On the same screen add a **Public hostname**: subdomain `dip`, your domain, service type **HTTP**, URL **`frontend:80`**. Save.

### Switch it on (office PC)

```powershell
.\scripts\ops\configure-public-access.ps1 -Hostname dip.<yourdomain>
```

Paste the token when asked; it isn't shown or printed. The script switches
DIP to **production mode** (stricter security checks), starts the tunnel,
points the phone app at `https://dip.<yourdomain>/api`, and checks the public
address answers. Then restart `npm run go` and reload the app on each phone.

To take DIP offline again: `.\scripts\ops\configure-public-access.ps1 -Disable`.

### Keep it reachable

- The PC must stay **on and awake**: Settings → System → Power → *Sleep: Never* (when plugged in).
- Docker Desktop: *Settings → General → Start Docker Desktop when you sign in*. Keep the PC signed in.
- If DIP is unreachable from outside: `docker compose ps` (is `delivery_tunnel` up?) and `docker compose logs cloudflared --tail 30`.
- **UptimeRobot** (account on the owner's email) checks
  `https://dip.chicagocargocourier.com/api/health/ready` every 5 minutes and
  emails when it stops answering "ready". That page only says ready when the
  PC, internet, tunnel, server and database all work.

### Security once it's public

- The login pages are on the internet, so **every account needs a strong, unique password** (`set_user_password`). Remove accounts nobody uses.
- Logins are rate-limited, and the session key (`SECRET_KEY`) and device key (`DIAD_API_KEY`) live only in `.env`. Never share that file.

### Dashboard email code (Cloudflare Access, on since 2026-10-12)

Before the DIP login page appears, Cloudflare asks for an email address and
sends a **6-digit code** to it. Only listed emails get a code. The code is
needed once per browser every 24 hours; then log in to DIP as usual.

Set up in Cloudflare One (Zero Trust) → **Access controls**:

| Application | Destination | Policy | What it does |
|---|---|---|---|
| `dip` | `dip.chicagocargocourier.com` | **Owner** (Allow, Emails) | Dashboard needs the email code |
| `dip` | `dip.chicagocargocourier.com/api` | **Phones** (Bypass, Everyone) | Driver app and UptimeRobot get through; DIP's own login still applies |

Login methods (Integrations → Identity providers): **One-time PIN** (email
code) and **Cloudflare** (sign in with a Cloudflare account).

- **Give a dispatcher access:** Access controls → Policies → **Owner** →
  Include → Emails → add their email → Save. Also create their DIP account.
- **Remove access:** delete their email from **Owner** (and disable their DIP account).
- **Code email doesn't arrive:** check spam; it comes from Cloudflare
  (`noreply@notify.cloudflare.com`). Codes expire after a few minutes;
  request a new one.
- **Phones or UptimeRobot suddenly blocked:** the **Phones** policy must be
  **Bypass** (not Allow) with **Everyone**, attached to the `/api` application.
  "Allow + Everyone" still makes everyone log in.
- The `/api` path stays open on purpose (phones can't do the email code), so
  strong DIP passwords and the login rate limit still matter.

## 11. Customer tracking link and texts

Every package has a tracking code (`CCC-XXXXXXXX`) and a public page:
`https://dip.chicagocargocourier.com/track/CCC-XXXXXXXX`. No login. It shows
the status (Scheduled, Picked up / on its way, Delivered with the time), the
street it's going to and the promised time. It never shows names, phone
numbers, instructions, photos or where the van is. Search engines are told
not to list it, and it is rate-limited per visitor.

- **Send the link yourself:** Packages → **Copy tracking link** on the row,
  then paste it into a text or email to the customer.
- **Cloudflare:** the page must be outside the dashboard email code. In
  Access controls → Applications, a self-hosted application for
  `dip.chicagocargocourier.com` path **`track`** uses the **Phones** policy
  (Bypass, Everyone), the same as `/api`.

### Automatic texts (off until set up)

When texts are set up, the recipient's phone (the "Recipient phone" on the
job) gets at most two texts per package:

1. **Out for delivery**, when the driver scans or picks up the package,
   with the deliver-by time if there is one and the tracking link.
2. **Delivered**, when the driver confirms delivery, with the time.

Each is sent once, even if the package is scanned again. Packages without a
valid US phone number are skipped. Texts use **Twilio**; put these in `.env`
and restart the backend (`docker compose up -d backend`):

`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and either `TWILIO_FROM_NUMBER`
(e.g. `+13125550100`) or `TWILIO_MESSAGING_SERVICE_SID`. Optional:
`COMPANY_PHONE` (shown on the tracking page). US carriers require the
sending number to be registered (toll-free verification, or A2P 10DLC for a
local number) before texts are delivered reliably; Twilio's console walks
through it. Customers can reply STOP to opt out; Twilio handles that.
