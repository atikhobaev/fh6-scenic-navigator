package launcher_native

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"os/exec"
	"sync"
)

type ServerManager struct {
	mu          sync.Mutex
	cmd         *exec.Cmd
	lifetime    processLifetime
	newLifetime processLifetimeFactory
	exited      chan error
	logf        func(string)
}

func NewServerManager(logf func(string)) *ServerManager {
	return NewServerManagerWithLifetime(logf, newProcessLifetime)
}

func NewServerManagerWithLifetime(logf func(string), factory processLifetimeFactory) *ServerManager {
	return &ServerManager{exited: make(chan error, 1), logf: logf, newLifetime: factory}
}
func (s *ServerManager) Start(ctx context.Context, exe string, args []string, dir string) error {
	return s.StartEnv(ctx, exe, args, dir, nil)
}
func (s *ServerManager) StartEnv(ctx context.Context, exe string, args []string, dir string, env []string) error {
	for {
		select {
		case <-s.exited:
			continue
		default:
			goto drained
		}
	}
drained:
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.cmd != nil {
		return fmt.Errorf("server already running")
	}
	lifetime, e := s.newLifetime()
	if e != nil {
		return e
	}
	cmd := exec.CommandContext(ctx, exe, args...)
	cmd.Dir = dir
	if env != nil {
		cmd.Env = env
	}
	configureHiddenProcess(cmd)
	stdout, e := cmd.StdoutPipe()
	if e != nil {
		return e
	}
	stderr, e := cmd.StderrPipe()
	if e != nil {
		return e
	}
	if e = cmd.Start(); e != nil {
		_ = lifetime.Close()
		return e
	}
	if e = lifetime.Assign(cmd.Process.Pid); e != nil {
		_ = cmd.Process.Kill()
		_ = lifetime.Close()
		_, _ = cmd.Process.Wait()
		return e
	}
	s.cmd = cmd
	s.lifetime = lifetime
	go s.scan(stdout)
	go s.scan(stderr)
	go func() {
		e := cmd.Wait()
		_ = lifetime.Close()
		s.mu.Lock()
		if s.cmd == cmd {
			s.cmd = nil
			if s.lifetime == lifetime {
				s.lifetime = nil
			}
		}
		s.mu.Unlock()
		s.exited <- e
	}()
	return nil
}
func (s *ServerManager) scan(r io.Reader) {
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		if s.logf != nil {
			s.logf(sc.Text())
		}
	}
}
func (s *ServerManager) Stop() error {
	s.mu.Lock()
	cmd := s.cmd
	lifetime := s.lifetime
	s.mu.Unlock()
	if cmd == nil || cmd.Process == nil {
		return nil
	}
	var err error
	if lifetime != nil {
		err = lifetime.Terminate()
	}
	if err != nil || lifetime == nil {
		if killErr := cmd.Process.Kill(); err == nil {
			err = killErr
		}
	}
	return err
}
func (s *ServerManager) Exited() <-chan error { return s.exited }
func (s *ServerManager) Running() bool        { s.mu.Lock(); defer s.mu.Unlock(); return s.cmd != nil }
