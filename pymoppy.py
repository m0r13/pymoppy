#!/usr/bin/env python

import midi
import serial
import sys
import time

from mingus.containers.Note import Note
from mingus.core import notes
from mingus.midi import fluidsynth

class MidiPlayer(object):
	def __init__(self):
		super(MidiPlayer, self).__init__()
	
	def note_on(self, channel, pitch, velocity=100):
		pass
	
	def note_off(self, channel, pitch, velocity=100):
		pass
	
	def control_change(self, channel, control, value):
		pass
	
	def set_instrument(self, channel, instrument):
		pass

class FluidsynthPlayer(MidiPlayer):
	def __init__(self, *args, **kwargs):
		super(FluidsynthPlayer, self).__init__()
		
		fluidsynth.init("/usr/share/sounds/sf2/FluidR3_GM.sf2", "alsa")
	
	def note_on(self, channel, pitch, velocity=100):
		note = Note()
		note.from_int(pitch)
		note.velocity = velocity
		fluidsynth.play_Note(note, channel)
	
	def note_off(self, channel, pitch, velocity=100):
		note = Note()
		note.from_int(pitch)
		note.velocity = velocity
		fluidsynth.stop_Note(note, channel)
	
	def control_change(self, channel, control, value):
		fluidsynth.control_change(channel, control, value)
	
	def set_instrument(self, channel, instrument):
		fluidsynth.set_instrument(channel, instrument)

class FloppyPlayer(MidiPlayer):
	def __init__(self, tty, baudrate = 9600, *args, **kwargs):
		super(FloppyPlayer, self).__init__()
		
		self.serial = serial.Serial(tty, baudrate)
		
		p1 = (24, 30578)
		p2 = (24 + 3*12 + 11, 2025)
		y = p1[1] / float(p2[1])
		x = p1[0] - p2[0]
		a = y ** (1. / x)
		b = p1[1] / float(a**p1[0])
		
		self.get_period = lambda x, a=a, b=b: int(b * a**x)
		self.resolution = 40
	
	def write_channel(self, channel):
		self.serial.write(chr(channel * 2 + 2))
	
	def write_pitch(self, pitch):
		period = self.get_period(pitch) / (self.resolution * 2)
		self.serial.write(chr((period >> 8) & 0xff))
		self.serial.write(chr(period & 0xff))
	
	def note_on(self, channel, pitch, velocity=100):
		self.write_channel(channel)
		self.write_pitch(pitch - 2*12)
		self.serial.flush()
	
	def note_off(self, channel, pitch, velocity=100):
		self.write_channel(channel)
		self.serial.write("\x00\x00")
		self.serial.flush()
	
	def reset(self, reverse=False):
		self.serial.write("\x65\x00\x00" if reverse else "\x64\x00\x00")

def ticktime(tempo, resolution):
	return 60. / float(tempo) / float(resolution)

def play(filename, player):
	queue = {}
	
	tempo, resolution = 120, 96
	timepertick = 0

	m = midi.read_midifile(filename)
	m.make_ticks_abs()
	for i, track in enumerate(m):
		for event in track:
			if event.tick not in queue:
				queue[event.tick] = []
			queue[event.tick].append(event)
			if isinstance(event, midi.SetTempoEvent):
				print event, event.bpm, event.mpqn
				tempo = event.get_bpm()
				
				timepertick = event.get_mpqn() / 100000000.
	
	print "%f %f " % (timepertick, ticktime(tempo, resolution))

	ticks = sorted(queue.keys())
	for i, tick in enumerate(ticks):
		for event in queue[tick]:
			if isinstance(event, midi.NoteOnEvent):
				player.note_on(event.channel, event.pitch, event.velocity)
			elif isinstance(event, midi.NoteOffEvent):
				player.note_off(event.channel, event.pitch, event.velocity)
			elif isinstance(event, midi.ControlChangeEvent):
				player.control_change(event.channel, event.control, event.value)
			elif isinstance(event, midi.ProgramChangeEvent):
				player.set_instrument(event.channel, event.value)

		if i < len(ticks) - 1:
			next_tick = ticks[i+1]
			diff = next_tick - tick
			time.sleep(diff * timepertick * 0.25)

if __name__ == "__main__":	
	player = FluidsynthPlayer()
	#player = FloppyPlayer("/dev/ttyACM0")
	
	play(sys.argv[1], player)
