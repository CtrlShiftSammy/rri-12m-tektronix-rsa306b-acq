#ifndef RSA_API_H
#define RSA_API_H

#include <stdint.h>

// Return status codes
typedef enum {
    noError = 0,
    errorNotConnected = -1,
    errorParameter = -2,
    errorTimeout = -3,
    errorTransfer = -4,
    errorDataNotReady = -5,
    errorIncompatibleFirmware = -6,
    errorLOLockFailure = -7,
    errorExternalReferenceNotEnabled = -8
} ReturnStatus;

// Device search constants
#define DEVSRCH_MAX_NUM_DEVICES 20
#define DEVSRCH_SERIAL_MAX_STRLEN 100
#define DEVSRCH_TYPE_MAX_STRLEN 20
#define DEVINFO_MAX_STRLEN 100

// IF Stream constants
#define IFSSDFN_SUFFIX_NONE -1
#define IFSSDFN_SUFFIX_TIMESTAMP 1
#define IFSSDFN_SUFFIX_INCRINDEX 0

// IF Stream modes
typedef enum {
    StreamingModeFormatted = 0,
    StreamingModeFramed = 1
} StreamingMode;

// IF Stream output destination
typedef enum {
    IFSOD_FILE_R3F = 0,
    IFSOD_CLIENT = 1
} IFSOUTDEST;

// IF Stream output format
typedef enum {
    IFSOF_INT16 = 0,
    IFSOF_FLOAT32 = 1
} IFSOUTFORMAT;

// Spectrum trace types
typedef enum {
    SpectrumTrace1 = 0,
    SpectrumTrace2 = 1,
    SpectrumTrace3 = 2
} SpectrumTraces;

// Complex data type
typedef struct {
    float i;
    float q;
} Cplx32;

// Spectrum settings structure
typedef struct {
    double span;
    double rbw;
    double actualStartFreq;
    double actualStopFreq;
    double actualFreqStepSize;
    int traceLength;
    int acqDataStatus;
} Spectrum_Settings;

// Spectrum trace info
typedef struct {
    int acqDataStatus;
} Spectrum_TraceInfo;

// DPX frame buffer structure
typedef struct {
    int fftCount;
    int frameCount;
    int spectrumBitmapWidth;
    int spectrumBitmapHeight;
    int sogramBitmapWidth;
    int sogramBitmapHeight;
    int sogramBitmapNumValidLines;
} DPX_FrameBuffer;

// Trigger modes
typedef enum {
    TriggerModeAutoLevel = 0,
    TriggerModeFreeRun = 1,
    TriggerModeTriggered = 2
} TriggerMode;

// Trigger sources
typedef enum {
    TriggerSourceIFPowerLevel = 0,
    TriggerSourceExternal = 1,
    TriggerSourceGPS_1PPS = 2,
    TriggerSourceGPS_1PPS_Sync = 3
} TriggerSource;

// IQ Stream output destinations
typedef enum {
    IQSOD_CLIENT = 0,
    IQSOD_FILE_SIQ = 1,
    IQSOD_FILE_SIQ_SPLIT = 2,
    IQSOD_FILE_TIQ = 3
} IQSOUTDEST;

// IQ Stream data types
typedef enum {
    IQSODT_SINGLE = 0,
    IQSODT_INT32 = 1,
    IQSODT_INT16 = 2
} IQSOUTDTYPE;

// IQ Stream file info
typedef struct {
    uint32_t acqStatus;
    double centerFreq;
    double sampleRate;
    double bandwidth;
    uint64_t samples;
    char filename[256];
} IQSTRMFILEINFO;

// IQ Stream status flags
#define IQSTRM_STATUS_OVERRANGE         0x00000001
#define IQSTRM_STATUS_XFER_DISCONTINUITY 0x00000002
#define IQSTRM_STATUS_IBUFF75PCT        0x00000004
#define IQSTRM_STATUS_IBUFFOVFLOW       0x00000008
#define IQSTRM_STATUS_OBUFF75PCT        0x00000010
#define IQSTRM_STATUS_OBUFFOVFLOW       0x00000020

// DPX trace types
typedef enum {
    TraceTypeAverage = 0,
    TraceTypeMaxHold = 1,
    TraceTypeMinHold = 2
} TraceType;

// DPX vertical units
typedef enum {
    VerticalUnit_dBm = 0,
    VerticalUnit_Watt = 1,
    VerticalUnit_Volt = 2,
    VerticalUnit_Amp = 3,
    VerticalUnit_dBmV = 4
} VerticalUnit;

#ifdef __cplusplus
extern "C" {
#endif

// Function declarations (these would normally be loaded dynamically)
// Device functions
ReturnStatus DEVICE_GetAPIVersion(char* version);
ReturnStatus DEVICE_Search(int* numDevices, int* deviceIDs, 
                          char deviceSerial[][DEVSRCH_SERIAL_MAX_STRLEN], 
                          char deviceType[][DEVSRCH_TYPE_MAX_STRLEN]);
ReturnStatus DEVICE_Connect(int deviceID);
ReturnStatus DEVICE_Disconnect();
ReturnStatus DEVICE_GetSerialNumber(char* serialNumber);
ReturnStatus DEVICE_Run();
ReturnStatus DEVICE_Stop();
const char* DEVICE_GetErrorString(ReturnStatus error);

// Configuration functions
ReturnStatus CONFIG_Preset();
ReturnStatus CONFIG_SetCenterFreq(double cf);
ReturnStatus CONFIG_SetReferenceLevel(double refLevel);
ReturnStatus CONFIG_GetCenterFreq(double* cf);
ReturnStatus CONFIG_GetReferenceLevel(double* refLevel);

// IF Streaming functions
ReturnStatus IFSTREAM_SetDiskFilePath(const char* filePath);
ReturnStatus IFSTREAM_SetDiskFilenameBase(const char* filenameBase);
ReturnStatus IFSTREAM_SetDiskFilenameSuffix(int suffixCtl);
ReturnStatus IFSTREAM_SetDiskFileLength(long fileLength);
ReturnStatus IFSTREAM_SetDiskFileMode(int mode);
ReturnStatus IFSTREAM_SetDiskFileCount(int fileCount);
ReturnStatus IFSTREAM_SetEnable(bool enable);
ReturnStatus IFSTREAM_GetActiveStatus(bool* isActive);
ReturnStatus IFSTREAM_SetOutputConfiguration(IFSOUTDEST dest, IFSOUTFORMAT format);

// Spectrum functions
ReturnStatus SPECTRUM_SetEnable(bool enable);
ReturnStatus SPECTRUM_SetDefault();
ReturnStatus SPECTRUM_GetSettings(Spectrum_Settings* settings);
ReturnStatus SPECTRUM_SetSettings(Spectrum_Settings settings);
ReturnStatus SPECTRUM_AcquireTrace();
ReturnStatus SPECTRUM_WaitForTraceReady(int timeoutMsec, bool* ready);
ReturnStatus SPECTRUM_GetTrace(SpectrumTraces trace, int maxTracePoints, 
                              float* traceData, int* outTracePoints);
ReturnStatus SPECTRUM_GetTraceInfo(Spectrum_TraceInfo* traceInfo);

// IQ Block functions
ReturnStatus IQBLK_SetIQBandwidth(double iqBandwidth);
ReturnStatus IQBLK_SetIQRecordLength(int recordLength);
ReturnStatus IQBLK_GetIQSampleRate(double* sampleRate);
ReturnStatus IQBLK_AcquireIQData();
ReturnStatus IQBLK_WaitForIQDataReady(int timeoutMsec, bool* ready);
ReturnStatus IQBLK_GetIQDataCplx(Cplx32* iqData, int* outLength, int reqLength);

// IQ Streaming functions
ReturnStatus IQSTREAM_SetAcqBandwidth(double bandwidth);
ReturnStatus IQSTREAM_SetOutputConfiguration(IQSOUTDEST dest, IQSOUTDTYPE dataType);
ReturnStatus IQSTREAM_SetDiskFilenameBase(const char* filenameBase);
ReturnStatus IQSTREAM_SetDiskFilenameSuffix(int suffixCtl);
ReturnStatus IQSTREAM_SetDiskFileLength(int msec);
ReturnStatus IQSTREAM_GetAcqParameters(double* bandwidth, double* sampleRate);
ReturnStatus IQSTREAM_Start();
ReturnStatus IQSTREAM_Stop();
ReturnStatus IQSTREAM_GetDiskFileWriteStatus(bool* complete, bool* writing);
ReturnStatus IQSTREAM_GetDiskFileInfo(IQSTRMFILEINFO* fileInfo);

// DPX functions
ReturnStatus DPX_SetEnable(bool enable);
ReturnStatus DPX_SetParameters(double span, double rbw, int bitmapWidth, int tracePtsPerPixel,
                              VerticalUnit verticalUnit, double yTop, double yBottom,
                              bool infinitePersistence, double persistenceTimeSec,
                              bool showOnlyTrigFrame);
ReturnStatus DPX_SetSogramParameters(double timePerDivisionSec, double timeResolutionSec,
                                    double yTop, double yBottom);
ReturnStatus DPX_Configure(bool enableSpectrum, bool enableSpectrogram);
ReturnStatus DPX_SetSpectrumTraceType(int traceIndex, TraceType traceType);
ReturnStatus DPX_IsFrameBufferAvailable(bool* frameAvailable);
ReturnStatus DPX_WaitForDataReady(int timeoutMsec, bool* ready);
ReturnStatus DPX_GetFrameBuffer(DPX_FrameBuffer* frameBuffer);
ReturnStatus DPX_FinishFrameBuffer();

// Trigger functions
ReturnStatus TRIG_SetTriggerMode(TriggerMode triggerMode);
ReturnStatus TRIG_SetIFPowerTriggerLevel(double level);
ReturnStatus TRIG_SetTriggerSource(TriggerSource triggerSource);
ReturnStatus TRIG_SetTriggerPositionPercent(double triggerPositionPercent);

// Playback functions
ReturnStatus PLAYBACK_OpenDiskFile(const wchar_t* filename, int startPercentage,
                                  int stopPercentage, double skipTime, bool loopAtEnd,
                                  bool realTime);
ReturnStatus PLAYBACK_GetReplayComplete(bool* complete);

#ifdef __cplusplus
}
#endif

#endif // RSA_API_H