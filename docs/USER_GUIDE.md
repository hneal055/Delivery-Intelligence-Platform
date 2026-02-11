# Delivery Intelligence Platform - User Guide

This guide covers the two main applications: the **Dispatcher Web UI** (for managers and dispatchers) and the **Mobile Driver App** (for delivery drivers).

---

## Table of Contents

**Part 1: Dispatcher Web UI**
1. [Logging In](#1-logging-in-web)
2. [Dashboard](#2-dashboard)
3. [Job Scheduling](#3-job-scheduling)
4. [GPS Tracking](#4-gps-tracking)
5. [Drivers](#5-drivers)
6. [Packages](#6-packages)
7. [Proof of Delivery Gallery](#7-proof-of-delivery-gallery)
8. [Equipment Management](#8-equipment-management)

**Part 2: Mobile Driver App**
9. [Logging In](#9-logging-in-mobile)
10. [Delivery List](#10-delivery-list)
11. [Delivery Detail & Actions](#11-delivery-detail--actions)
12. [Profile & GPS Status](#12-profile--gps-status)

**Appendix**
- [User Accounts & Roles](#user-accounts--roles)
- [Keyboard Shortcuts & Tips](#keyboard-shortcuts--tips)

---

# Part 1: Dispatcher Web UI

The Dispatcher Web UI is a browser-based dashboard for managing fleet operations, scheduling jobs, tracking drivers, and reviewing delivery proofs. Access it at `http://localhost:5173` after starting the dev server (`cd src/web && npm run dev`).

## 1. Logging In (Web)

Open the application in your browser. You will see the **Dispatcher Console** login form.

| Field    | Default Value         |
|----------|-----------------------|
| Username | `dispatcher1`         |
| Password | `dispatcherpassword`  |

Enter your credentials and click **Sign In**. If login fails, a red error message appears below the password field. On success, you are redirected to the Dashboard.

The left sidebar provides navigation to all pages: Dashboard, Scheduling, Drivers, Packages, Proof Gallery, Tracking, and Equipment. Your username and role are shown in the top-right header alongside a **Logout** button.

---

## 2. Dashboard

The Dashboard is the primary overview screen, split into two sections:

### Stats Bar (Top)

A row of metric cards showing real-time fleet statistics:

| Metric           | Description                              |
|------------------|------------------------------------------|
| Online Drivers   | Drivers with a heartbeat in the last 60s |
| Active Drivers   | Drivers with an "active" status          |
| Pending Packages | Packages awaiting delivery               |
| Delivered        | Successfully delivered packages          |
| Total Drivers    | Total registered drivers                 |
| Total Packages   | Total packages in the system             |
| Exceptions       | Packages flagged with delivery issues    |

### Map & Driver List (Main Area)

- **Left (Map)**: An interactive OpenStreetMap showing all drivers as markers. Click any marker to select that driver and highlight them.
- **Right (Driver List)**: A scrollable list of driver cards showing each driver's name, status, and online indicator. Click a card to select/deselect a driver on the map. The selected driver card is highlighted.

If no drivers appear, the fleet simulator may not be running. Start it with `.\start_platform.ps1` or `.\run_simulation.ps1 -Drivers 50`.

---

## 3. Job Scheduling

The Scheduling page manages dispatch jobs through their lifecycle: **Pending -> Assigned -> In Progress -> Completed**.

### View Modes

Toggle between two views using the segmented control in the top-right:

- **Table View**: A sortable data table with columns for Title, Scheduled time, Priority, Assignment status, Status, and Actions.
- **Board View**: A Kanban-style board with four columns (Pending, Assigned, In Progress, Completed). Each column shows a count badge and job cards.

### Creating a Job

1. Click the **Create Job** button (top-right).
2. Fill out the form:
   - **Title** (required): Name of the delivery job.
   - **Type**: Delivery, Pickup, or Service.
   - **Priority**: Low, Medium, High, or Urgent.
   - **Scheduled Time**: Date/time picker for when the job should be executed.
   - **Notes**: Optional free-text for special instructions.
3. Click **Create**.

### Assigning a Driver

1. On an unassigned job, click the **Assign** button.
2. The Assignment Modal opens, showing available drivers sorted by:
   - Online drivers first
   - Then by lowest current package count (least busy first)
3. Each driver option shows their online/offline status and current workload.
4. Select a driver and click **Assign**.

### Filtering (Table View)

Use the **Filter by status** dropdown above the table to show only jobs in a specific state (Pending, Assigned, In Progress, Completed, or Cancelled). Clear the filter to show all jobs.

### Job Actions

**From the Table**: Each row has an actions column with:
- **Assign** button (if unassigned)
- **Menu** (three dots icon) with status changes (Pending, In Progress, Completed, Cancelled) and a red **Delete Job** option

**From the Job Detail Drawer**: Click any job row (table) or card (board) to open a slide-out drawer on the right showing:
- Job title, status/priority/type badges
- Scheduled date and completion date (if applicable)
- Assigned driver with online status
- Job notes
- Action buttons: **Assign**, **Start**, **Complete**, or **Cancel** (context-dependent)

---

## 4. GPS Tracking

The Tracking page provides real-time driver location monitoring and historical route playback.

### Selecting a Driver

Use the **Select Driver** dropdown (top-left panel) to pick a driver. The dropdown is searchable and shows each driver's online/offline status. Once selected, a driver info card appears showing:
- Driver name
- Online/Offline and status badges
- Current package count
- Number of location history points available

### Real-Time Map

The map displays all drivers as markers with live position updates via WebSocket. The selected driver's route history is shown as a colored polyline.

### Route Playback

When a driver is selected and has location history, playback controls appear below the info card:

| Control         | Action                                                |
|-----------------|-------------------------------------------------------|
| Play/Pause      | Start or pause animated playback through the route    |
| Stop            | Reset playback to the beginning                       |
| Speed Selector  | Choose playback speed: 1x, 2x, 5x, or 10x           |
| Timeline Slider | Drag to scrub to any point in the route history       |
| Current Time    | Shows the timestamp of the current playback position  |

During playback, the map shows traveled path (solid line) and remaining path (dashed line) with an animated marker moving along the route.

---

## 5. Drivers

The Drivers page is a data table listing all registered drivers.

### Searching & Filtering

- **Search bar**: Type a driver name or ID to filter the list in real-time.
- **Status filter**: Dropdown to show only Active or Inactive drivers.

### Table Columns

| Column       | Description                                       |
|--------------|---------------------------------------------------|
| Name         | Driver's full name                                |
| Status       | Active (blue) or Inactive (gray) badge            |
| Online       | Green dot = online, gray dot = offline             |
| Packages     | Number of packages currently assigned              |
| Location     | Current GPS coordinates (lat, lon) or "N/A"        |
| Last Updated | Timestamp of the driver's most recent data update  |

---

## 6. Packages

The Packages page lists all packages in the system with status tracking.

### Filtering

Use the **Filter by status** dropdown to view packages by state:
- **Pending** (orange): Awaiting pickup or delivery
- **Loaded** (blue): On the truck
- **Delivered** (teal): Successfully delivered
- **Exception** (red): Delivery issue reported

### Table Columns

| Column      | Description                                          |
|-------------|------------------------------------------------------|
| Package ID  | Unique identifier (truncated in display)             |
| Status      | Color-coded badge                                    |
| Driver      | Assigned driver ID or "Unassigned"                   |
| Destination | Street address or GPS coordinates                    |
| ETA (sec)   | Predicted time to delivery from the ML model         |
| Created     | Package creation timestamp                           |

---

## 7. Proof of Delivery Gallery

The Proof Gallery displays photos captured by drivers as proof of successful delivery.

### Filtering

Two filter controls appear at the top of the page:

- **Search**: Type a package ID or driver ID to narrow results.
- **Date Range**: Select from Today, Last 7 days, Last 30 days, or All.

### Viewing Proofs

Proofs are displayed in a responsive grid (1-4 columns depending on screen width). Each card shows:
- Thumbnail image
- Package ID badge
- Driver ID badge
- Capture timestamp

Click any card to open a **Detail Modal** with the full-size image and all metadata.

If no proofs are found, an empty state with a photo icon is displayed. Proofs are auto-refreshed every 60 seconds.

---

## 8. Equipment Management

The Equipment page tracks physical equipment (scanners, dollies, radios, vehicle keys) with barcode-based check-in/out.

### Summary Cards

Three stat cards at the top show:
- **Total**: All registered equipment
- **Available** (green): Ready for use
- **Checked Out** (orange): Currently assigned to someone

### Adding Equipment

1. Click **Add Equipment** (top-right).
2. Fill out the form:
   - **Name** (required): Equipment description
   - **Barcode** (required): Physical barcode ID (can be entered manually or scanned)
   - **Type**: Scanner, Dolly, Radio, Vehicle Key, or Other
   - **Notes**: Optional
3. Click **Add Equipment**.

### Scanning Barcodes (Check-In/Out)

1. Click the **Scan** button (top-right).
2. The scanner modal opens with a camera feed for barcode detection.
   - Grant camera permission when prompted.
   - Hold a barcode in front of the camera. Detection is automatic.
   - Alternatively, type the barcode manually in the text field below the camera.
3. Once a barcode is recognized:
   - If found in inventory: Equipment details and status are shown with a **Check In** or **Check Out** button.
   - If not found: A yellow warning suggests registering the equipment first.

### Equipment Table

Lists all equipment with columns: Name, Barcode, Type, Status, Current User, and action buttons (Check In / Check Out / Delete).

### Activity Timeline

Below the table, the most recent 10 check-in/out events are displayed as a timeline, showing the action type, barcode, driver, and timestamp.

> **Note**: Equipment data is stored in browser localStorage, so it persists across sessions but is not shared between browsers.

---

# Part 2: Mobile Driver App

The Mobile Driver App is a React Native (Expo) application for drivers to manage their deliveries, verify locations, capture proof, and report exceptions. Start it with `cd src/mobile && npx expo start --web`.

## 9. Logging In (Mobile)

The login screen has two fields pre-filled with demo credentials:

| Field    | Default Value     |
|----------|-------------------|
| Username | `driver1`         |
| Password | `driverpassword`  |

Enter credentials and tap **Login**. A loading spinner appears during authentication. On failure, an alert displays the error. On success, you are taken to the Delivery List.

---

## 10. Delivery List

The Delivery List shows all packages assigned to the logged-in driver.

Each delivery card displays:
- **Package ID**
- **Status badge**: Color-coded (green = delivered, orange = pending, red = exception, blue = loaded)
- **Destination**: Street address or GPS coordinates
- **ETA**: Estimated minutes to arrival

**Pull down** to refresh the list. Tap any card to open the Delivery Detail screen.

If the backend is unreachable, demo packages are shown automatically for testing.

---

## 11. Delivery Detail & Actions

The detail screen for a selected package has three sections:

### Smart ETA Prediction

- **Auto-Update toggle**: When ON, ETA recalculates automatically as your GPS position changes.
- **Traffic Selector**: Three buttons to set current traffic conditions:
  - Light (fast)
  - Moderate (medium)
  - Heavy (slow)
- **ETA Display**: Shows the ML-predicted arrival time in minutes. Displays "Calculating Route..." while computing.
- **Refresh ETA button**: Appears when Auto-Update is OFF for manual recalculation.

The ETA is calculated using your current GPS distance to the destination combined with the traffic load, sent to the ML prediction endpoint (`/analytics/predict-eta`).

### Package Information

- Package ID
- Destination address or coordinates
- Your current GPS position (if available)

### Delivery Actions

Execute these actions in order during a typical delivery:

1. **Verify GPS Location**: Sends your current GPS coordinates and the delivery target to the server. The server checks if you are within the geofence radius. Result appears as a status message (e.g., "Location verified" or "Too far from delivery point").

2. **Capture Proof of Delivery**: Opens the device camera. Take a photo of the delivered package. The photo thumbnail appears on screen after capture. Camera permission is requested on first use.

3. **Confirm Delivery**: Uploads the captured photo to the server as proof. This button is disabled until a photo is taken. On success, an alert confirms the delivery.

4. **Report Exception** (red button): Flags the delivery as failed with reason "Customer Unavailable". Use this when you cannot complete the delivery. An alert confirms the report was submitted.

---

## 12. Profile & GPS Status

The Profile screen (accessible via the bottom tab navigation) shows:

### Driver Profile
- Your Driver ID

### GPS Status
- **Latitude and Longitude**: Current coordinates with 6-decimal precision
- **Accuracy**: GPS accuracy in meters
- If GPS is unavailable, shows "Waiting for GPS signal..." or an error message

### Logout
A red **Logout** button at the bottom signs you out and returns to the login screen.

---

# Appendix

## User Accounts & Roles

| Username      | Password             | Role    | Access                        |
|---------------|----------------------|---------|-------------------------------|
| `admin`       | `adminpassword`      | Admin   | Full access (Web)             |
| `dispatcher1` | `dispatcherpassword` | Manager | Full dispatcher access (Web)  |
| `driver1`     | `driverpassword`     | Driver  | Mobile app + limited API      |

- **Admin / Manager** roles can connect to the WebSocket for real-time updates.
- **Driver** role is used exclusively by the mobile app.

## Keyboard Shortcuts & Tips

- **Dispatcher Web UI** runs best in Chrome or Edge. Firefox is supported.
- The **Barcode Scanner** requires a browser that supports the BarcodeDetector API (Chrome 83+) or falls back to a polyfill.
- Equipment data is stored in **browser localStorage**. Clearing browser data will reset the equipment inventory.
- The real-time map and driver online status require the **fleet simulator** to be running. Without it, all drivers appear offline.
- WebSocket connections require `uvicorn[standard]` on the backend. See the README Troubleshooting section if WebSocket connections fail.
