//go:build windows

package launcher_native

import (
	"fmt"
	"syscall"
	"unsafe"
)

const (
	jobObjectInfoClassExtendedLimit = 9
	jobObjectLimitKillOnJobClose    = 0x00002000
	processSetQuota                 = 0x0100
	processTerminate                = 0x0001
	processQueryLimitedInformation  = 0x1000
)

type jobObjectBasicLimitInformation struct {
	PerProcessUserTimeLimit int64
	PerJobUserTimeLimit     int64
	LimitFlags              uint32
	MinimumWorkingSetSize   uintptr
	MaximumWorkingSetSize   uintptr
	ActiveProcessLimit      uint32
	Affinity                uintptr
	PriorityClass           uint32
	SchedulingClass         uint32
}

type ioCounters struct {
	ReadOperationCount  uint64
	WriteOperationCount uint64
	OtherOperationCount uint64
	ReadTransferCount   uint64
	WriteTransferCount  uint64
	OtherTransferCount  uint64
}

type jobObjectExtendedLimitInformation struct {
	BasicLimitInformation jobObjectBasicLimitInformation
	IoInfo                ioCounters
	ProcessMemoryLimit    uintptr
	JobMemoryLimit        uintptr
	PeakProcessMemoryUsed uintptr
	PeakJobMemoryUsed     uintptr
}

type windowsProcessLifetime struct {
	job syscall.Handle
}

var (
	pCreateJobObject    = kernel32.NewProc("CreateJobObjectW")
	pSetInformationJob  = kernel32.NewProc("SetInformationJobObject")
	pAssignProcessToJob = kernel32.NewProc("AssignProcessToJobObject")
	pTerminateJob       = kernel32.NewProc("TerminateJobObject")
	pOpenProcess        = kernel32.NewProc("OpenProcess")
	pCloseHandle        = kernel32.NewProc("CloseHandle")
)

func newProcessLifetime() (processLifetime, error) {
	h, _, callErr := pCreateJobObject.Call(0, 0)
	if h == 0 {
		return nil, fmt.Errorf("CreateJobObjectW: %v", callErr)
	}
	job := syscall.Handle(h)
	info := jobObjectExtendedLimitInformation{}
	info.BasicLimitInformation.LimitFlags = jobObjectLimitKillOnJobClose
	r, _, callErr := pSetInformationJob.Call(
		uintptr(job),
		jobObjectInfoClassExtendedLimit,
		uintptr(unsafe.Pointer(&info)),
		unsafe.Sizeof(info),
	)
	if r == 0 {
		pCloseHandle.Call(uintptr(job))
		return nil, fmt.Errorf("SetInformationJobObject(KILL_ON_JOB_CLOSE): %v", callErr)
	}
	return &windowsProcessLifetime{job: job}, nil
}

func (w *windowsProcessLifetime) Assign(pid int) error {
	if w == nil || w.job == 0 {
		return fmt.Errorf("job object is closed")
	}
	access := uintptr(processSetQuota | processTerminate | processQueryLimitedInformation)
	h, _, callErr := pOpenProcess.Call(access, 0, uintptr(uint32(pid)))
	if h == 0 {
		return fmt.Errorf("OpenProcess(%d): %v", pid, callErr)
	}
	defer pCloseHandle.Call(h)
	r, _, callErr := pAssignProcessToJob.Call(uintptr(w.job), h)
	if r == 0 {
		return fmt.Errorf("AssignProcessToJobObject(%d): %v", pid, callErr)
	}
	return nil
}

func (w *windowsProcessLifetime) Terminate() error {
	if w == nil || w.job == 0 {
		return nil
	}
	r, _, callErr := pTerminateJob.Call(uintptr(w.job), 0)
	if r == 0 {
		return fmt.Errorf("TerminateJobObject: %v", callErr)
	}
	return nil
}

func (w *windowsProcessLifetime) Close() error {
	if w == nil || w.job == 0 {
		return nil
	}
	h := w.job
	w.job = 0
	r, _, callErr := pCloseHandle.Call(uintptr(h))
	if r == 0 {
		return fmt.Errorf("CloseHandle(job): %v", callErr)
	}
	return nil
}
