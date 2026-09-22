71ac20af38c7621709667387b7528cd82a9f4537
stabilization/2026-09
 M .gitignore
 M app.json
 M clean_start.ps1
 M daily_startup.ps1
 M docker-compose.yml
 M package-lock.json
 M package.json
 M src-ui/src/App.tsx
 M src-ui/src/components/FleetDashboard.tsx
 M src/mobile/App.js
 M src/mobile/app.json
 M tools/simulators/fleet_sim.py
?? BASELINE.md
?? initialize_backend.ps1
?? load_env.ps1
?? run_fleet_simulator.ps1
?? setup_secrets.ps1
?? src-ui/Dockerfile
?? src-ui/src/components/DriverManagementPanel.tsx
?? src/backend/alembic.ini
?? src/backend/alembic/
?? src/backend/init_db.py
?? start_all.ps1
?? tools/simulators/start_all.ps1
 .gitignore                               |     1 +
 app.json                                 |     5 +-
 clean_start.ps1                          |    83 +-
 daily_startup.ps1                        |   204 +-
 docker-compose.yml                       |     6 +-
 package-lock.json                        | 14353 ++++++++---------------------
 package.json                             |    12 +-
 src-ui/src/App.tsx                       |    41 +-
 src-ui/src/components/FleetDashboard.tsx |   206 +-
 src/mobile/App.js                        |   305 +-
 src/mobile/app.json                      |    34 +-
 tools/simulators/fleet_sim.py            |    11 +-
 12 files changed, 4343 insertions(+), 10918 deletions(-)
71ac20af Stabilize container build, fix database migrations, seed driver/admin profiles, and verify fleet simulation
a9df8065 chore: pin dependencies with hashes and stabilize test suite coverage
2c9cb097 test(delivery): ensure 100% test coverage on delivery_service
80141731 test(delivery): achieve 100% test coverage on delivery_service with robust unit tests
9b19179f Revise README.md with updated push instructions
3ec14225 Revise README.md for improved documentation
58e5ac7e Enhance README.md with quick start instructions
d2196434 Stabilize platform: Docker containerization, PostGIS migration, Redis integration, and fleet simulation
e089ad3b Phase 1A rebuild delivery route foundation
b02f29d0 Cleanup duplicate delivery route backups
0d587a24 Recovery checkpoint - backend startup restored
2965177e Command Center operational metrics integrated
27b9ba13 Update README with fleet simulation instructions
1fc9f686 Update README with build and launch instructions
b0437416 Update README with project details and setup instructions
fd9a3a0d fix(mobile): clean up app.json permissions schema for EAS build
948d616d fix(mobile): generate clean package-lock.json for EAS build
864c4e6d feat(mobile): complete Track B with native-free heartbeat network telemetry and autonomous queue sync
4547b236 feat(mobile): add full-bleed landscape orientation modal with Leaflet map fit and exit controls
569d906e feat(mobile): complete offline delivery store-and-forward queue with image compression and timeout safeguards
Python 3.14.2
v24.20.0
Client:
 Version:           29.5.3
 API version:       1.54
 Go version:        go1.26.4
 Git commit:        d1c06ef
 Built:             Wed Jun  3 18:03:06 2026
 OS/Arch:           windows/amd64
 Context:           desktop-linux

Server: Docker Desktop 4.78.0 (229452)
 Engine:
  Version:          29.5.3
  API version:      1.54 (minimum version 1.40)
  Go version:       go1.26.4
  Git commit:       285b471
  Built:            Wed Jun  3 17:59:56 2026
  OS/Arch:          linux/amd64
  Experimental:     false
 containerd:
  Version:          v2.2.4
  GitCommit:        193637f7ee8ae5f5aa5248f49e7baa3e6164966e
 runc:
  Version:          1.3.5
  GitCommit:        v1.3.5-0-g488fc13e
 docker-init:
  Version:          0.19.0
  GitCommit:        de40ad0
Docker Compose version v5.1.4
