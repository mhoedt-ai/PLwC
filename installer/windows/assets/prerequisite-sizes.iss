; Versioned estimates shown by the Windows installer.
; Download values are rounded up from the pinned vendor packages.
; The build overrides PlwcPayloadMiB with the staged uncompressed payload size.
#ifndef PlwcPayloadMiB
#define PlwcPayloadMiB 20
#endif
#define PythonDownloadMiB 115
#define PythonDiskMinMiB 450
#define PythonDiskMaxMiB 1050
#define QdrantModelMinMiB 100
#define QdrantModelMaxMiB 500
#define NodeDownloadMiB 32
#define NodeDiskMiB 100
#define DockerDownloadMiB 610
#define DockerDiskMinMiB 3072
#define SizeEstimateDate "2026-08-05"
