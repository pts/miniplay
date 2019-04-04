#! /usr/bin/python
#
# miniplay.py: minimalistic sound player for Linux ALSA in Python
# by pts@fazekas.hu at Thu Apr  4 12:55:11 CEST 2019
#
# miniplay.py pregenerates a 1-second-long audio sample and plays it in an
# infinite loop on a Linux ALSA sound card with aplay(1)
# (sudo apt-get install alsa-utils). It doesn't adjust the volume.
# miniplay.py can be used to play sine waves, square waves and square waves
# with data bits specified on the command-line.
#
# Use Ctrl-<C> to exit.
#
# Example usage:
#
#   $ ./miniplay.py -D default -T sin      # 440 Hz sine wave.
#   $ ./miniplay.py -D default -T sinlh    # Different sines on left, right.
#   $ ./miniplay.py -D default -T square   # 600 Hz square wave.
#   $ ./miniplay.py -D default -T bits:01  # Same as square, 1200 Hz bitrate.
#   $ ./miniplay.py -D default -T bits:00011  # 1200 Hz bitrate, square data.
#
# If you have sound card problems, drop the `-D default', or get a list of
# `-D' values from `aplay -L'. See /proc/asound/cards for CARD= arguments.
# See also /proc/asound/pcm .
#
# Typical useful ALSA device `-D' values on Debian Buster:
#
# * dmix : Mixing to the default sound card, so multip programs can play
#   at the same time. Doesn't use pulseuadio.
#   Sometimes it's ``Device or resource busy'' for 10 seconds, e.g. when
#   pulseaudio is playing something.
# * dmix:CARD=0,DEV=0
# * sysdefault : Seems to be equivalent to dmix. Doesn't use pulseudio.
# * sysdefault:CARD=0,DEV=0
# * default : Mixing with pulseaudio (/usr/share/alsa/pulse-alsa.conf).
#   Higher quality mixing than dmix if buffer is long.
# * hw:CARD=0,DEV=0  : ``Device or resource busy'' instead of mixing.
#   Doesn't use pulseaudio.
# * hw:CARD=PCH,DEV=0  : Specifies driver (PCH is Intel HDA).
#

import math
import subprocess
import struct
import sys


def main(argv):
  device = 'dmix'

  format = None

  rate = 48000

  tune = 'sinlh'

  i = 1
  while i < len(argv):
    arg = argv[i]
    if arg == '-':
      break
    i += 1
    if arg == '--':
      break
    elif arg == '-D' and i < len(argv):
      device = argv[i]
      i += 1
    elif arg == '-f' and i < len(argv):
      format = argv[i]
      i += 1
    elif arg == '-T' and i < len(argv):
      tune = argv[i]
      i += 1
    else:
      raise RuntimeError('Unknown flag: %s' % arg)
  if i != len(argv):
    raise RuntimeError('Too many command-line arguments.')
  if format is not None:
    pass
  elif device == 'dmix' or device.startswith('dmix:'):
    format = 'S32_LE'  # Doesn't support anything else.
  else:
    format = 'S16_LE'

  if format == 'S16_LE':
    fmt, maxv, sbs = '<hh', 32767, 2
  elif format == 'S16_BE':
    fmt, maxv, sbs = '>hh', 32767, 2
  elif format == 'S32_LE':
    fmt, maxv, sbs = '<ll', 2147483647, 4
  elif format == 'S32_LE':
    fmt, maxv, sbs = '>ll', 2147483647, 4
  else:
    raise RuntimeError('Unknown format: %s' % format)

  def get_data_for_bits(bitrate, bits):
    # bitrate is bits per second.
    if rate % bitrate:
      raise ValueError('Invalid rate %d, must be a multiple of %d.' %
                       (rate, bitrate))
    s = len(bits)
    if s > bitrate:
      raise ValueError('Too many bits of data.')
    rss = rate / bitrate
    v01 = (struct.pack(fmt, -maxv, -maxv), struct.pack(fmt, maxv, maxv))
    return ''.join(v01[bits[i % s] not in '0\0'] * rss for i in xrange(bitrate))

  hz = 440
  m = math.pi * 2 * hz / rate
  if tune in ('sin', 'sine'):
    data = ''.join(
       struct.pack(fmt, int(math.sin(i * m) * maxv),  # Left.
                        int(math.sin(i * m) * maxv))  # Right.
       for i in xrange(rate))  # Generate 1 second of data.
  elif tune == 'sinlh':
    data = ''.join(
       struct.pack(fmt, int(math.sin(i * m / 4) * maxv),  # Left, low pitch.
                        int(math.sin(i * m) * maxv))  # Right.
       for i in xrange(rate))  # Generate 1 second of data.
  elif tune == 'sinl':
    data = ''.join(
       struct.pack(fmt, int(math.sin(i * m / 4) * maxv),  # Left, low pitch.
                        0)  # Right, silent.
       for i in xrange(rate))  # Generate 1 second of data.
  elif tune == 'sinh':
    data = ''.join(
       struct.pack(fmt, 0,  # Left, silent.
                        int(math.sin(i * m) * maxv))  # Right.
       for i in xrange(rate))  # Generate 1 second of data.
  elif tune == 'square':  # 600 Hz square wave, 1200 samples per second.
    data = get_data_for_bits(1200, '01')
  elif tune.startswith('bits:'):
    # Example tune: bits:0001
    data = get_data_for_bits(1200, tune.split(':', 1)[1])
  else:
    raise RuntimeError('Unknown tune: %s' % tune)
  assert len(data) == rate * sbs * 2

  cmd = ('aplay', '-D', device, '-f', format, '-c', '2', '-r', str(rate), '-q')
  p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
  try:
    try:
      while 1:
        p.stdin.write(data)
        p.stdin.flush()
    finally:
      try:
        p.stdin.close()
      except (OSError, IOError):
        pass
      exit_code = p.wait()
    if exit_code:
      raise RuntimeError('%s failed with exit code %d' % (cmd, exit_code))
  except KeyboardInterrupt:
    pass


if __name__ == '__main__':
  sys.exit(main(sys.argv))
