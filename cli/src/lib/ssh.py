import paramiko
import socket
import os
import sys
import termios
import tty
import select
# import shutil
import signal
import fcntl
import termios
import struct

# Setup raw terminal for interactive shell
def interactive_shell(chan):
    oldtty = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        chan.settimeout(0.0)

        while True:
            r, _, _ = select.select([chan, sys.stdin], [], [])
            if chan in r:
                try:
                    x = chan.recv(1024)
                    if len(x) == 0:
                        break
                    sys.stdout.buffer.write(x)
                    sys.stdout.flush()
                except socket.timeout:
                    pass
            if sys.stdin in r:
                x = sys.stdin.read(1)
                if len(x) == 0:
                    break
                chan.send(x)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

def connect_to_jump(jump_host, jump_port, jump_user, target_host, target_port):
    jump_client = paramiko.SSHClient()
    jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"[*] Connecting to jump host {jump_host}:{jump_port} as {jump_user}...")
    jump_client.connect(jump_host, port=jump_port, username=jump_user)

    # Open a tunnel from the jump host to the target host
    print(f"[*] Opening tunnel to {target_host}:{target_port} through jump host...")
    jump_transport = jump_client.get_transport()
    dest_addr = (target_host, target_port)
    local_addr = ('', 0)
    tunnel = jump_transport.open_channel("direct-tcpip", dest_addr, local_addr)

    return jump_client, tunnel

def connect_via_jump(jump_host, jump_port, jump_user,
           target_host, target_port, target_user, target_password):

  # Connect to the jump host if needed
  tunnel = None
  if jump_host is not None:
    jump_client, tunnel = connect_to_jump(jump_host=jump_host,
                                          jump_port=jump_port,
                                          jump_user=jump_user,
                                          target_host=target_host,
                                          target_port=target_port)

  # Now connect to target host through the tunnel
  target_client = paramiko.SSHClient()
  target_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  print(f"[*] Connecting to target host {target_host}:{target_port} as {target_user}... (jump: {jump_host})")
  target_client.connect(target_host, port=target_port, username=target_user, password=target_password, sock=tunnel)
  chan = target_client.invoke_shell()

  # adjust terminal to window size
  def handle_sigwinch(signum, frame):
    s = struct.pack("HHHH", 0, 0, 0, 0)
    size = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s)
    rows, cols = struct.unpack("HHHH", size)[:2]
    chan.resize_pty(width=cols, height=rows)

  signal.signal(signal.SIGWINCH, handle_sigwinch)
  handle_sigwinch(None, None)

  print(f"[*] Connected. Starting interactive shell...\n")
  interactive_shell(chan)
  chan.close()
  target_client.close()
  if jump_host is not None:
    jump_client.close()

if __name__ == '__main__':
  # Example usage
  connect_via_jump(
      jump_host='duckburg.net.in.tum.de',
      jump_port=10022,
      jump_user='dsaucezi',
      target_host='172.28.2.108',
      target_port=22,
      target_user='ubuntu',
      target_password='password'
  )
