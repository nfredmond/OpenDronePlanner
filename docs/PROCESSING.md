# From flight media to a delivery

1. Open **Process & present**. Create a capture from the current plan, or choose a capture without a plan for an existing image survey.
2. Drop the flight media or choose its folder. Originals are copied and checksummed. File names must be unique within a capture. Use separate captures for flights with repeated camera filenames. Review photo counts, GPS positions and metadata warnings.
3. Install Docker once if needed, then start it. In ODP choose CPU or optional NVIDIA CUDA and click **Start engine**. First use downloads several GB. The engine stays local and ODP opens its own free port.
4. Choose **Reconstruction** and a preset. Map and elevation requests an orthomosaic, DSM, DTM and classified point cloud. Load all supported options to adjust the engine. Start reconstruction and follow **Results** or the processing log.
5. Open **Full WebODM workspace** to inspect the orthomosaic, point cloud or model and use upstream tools. Runs created there are also protected against accidental app shutdown.
6. In **Report & delivery**, enter field conditions, findings and limitations, then save. Download the printable report or small metadata packet. In **Results**, choose output files and build a ZIP that includes the actual products plus the report and checksums.
7. Close the desktop window when work is finished. Active processing, imports and delivery builds must finish or be canceled before services stop. Captures, engine results and report notes remain for the next session. Nothing starts at login.

## Inputs and outputs

Supported video extensions are MP4, MOV, LRV and TS. Include matching SRT telemetry when available. Name ground control `gcp_list.txt` and optional image geolocation overrides `geo.txt`, using the running engine's format. Other accepted sidecars are archived as field records. They are not silently treated as photos. Video extraction, multispectral, thermal and GCP workflows depend on the upstream engine and suitable inputs.

The map of EXIF photo positions is not a flight track or an overlap assessment. Ground sample distance is pixel size, not positional accuracy. Review coordinate/vertical references, artifacts, control points and independent checkpoints before using reconstructed measurements.

The report is HTML and prints to PDF from a browser. The engine provides its own quality PDF. The small delivery packet contains metadata, report and linked plan. The Results ZIP includes the selected actual processing outputs, with separate output checksums. Choosing `all.zip` nests the engine's complete archive inside the delivery.

## CPU and GPU

CPU mode works without an NVIDIA card. CUDA mode probes Docker GPU access and refuses to claim acceleration when that probe fails. Install the NVIDIA Container Toolkit on Linux or configure supported WSL2 GPU access on Windows. CUDA accelerates supported stages; other stages still use CPU and memory. Mac computers use CPU processing. The desktop is native on Apple Silicon; the pinned Linux x64 engine currently uses Docker emulation there.

ODP processes one reconstruction at a time per node, with the chosen CPU thread limit and a 16 GB memory limit. Large surveys may require splitting or a separately configured WebODM installation. The default is suitable for a small photo survey, not a promise that every dataset fits.

## Local storage and recovery

ODP owns the Compose project `odp-processing`. It does not reconfigure another WebODM installation. Media records and local engine settings are under the ODP data directory; the database and products are in its named Docker volumes. Preserve both when backing up. Do not delete volumes to repair a startup issue.

After an interrupted desktop session, **Start engine** reconnects to an existing ODP stack. Finish its jobs before changing acceleration. A failed media upload retains its record; source originals remain unchanged. Retrying reconstruction creates a new run. It does not overwrite a completed result.
