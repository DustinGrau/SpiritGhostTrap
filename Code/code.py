# Ghostbusters Ghost Trap - Device Control
#
# Laser Relay = 3V + D7
# Audio Out   = 3V + A0
# Taunt Seq.  = D0
# Door Open   = D1
# Trap Seq.   = D2
# Servos1/2   = D3/D4
# White LED   = D5 (was A2)
# Indicator   = D9
# Bar Graph   = D10/D11/D12 (Gnd + 220ohm)
#
import audioio
import board
import neopixel
import time
from adafruit_led_animation.color import BLACK, GREEN, WHITE
from adafruit_motor import servo
from audiocore import WaveFile
from digitalio import DigitalInOut, Direction, Pull
from pwmio import PWMOut

try:
    from audioio import AudioOut
except ImportError:
    try:
        from audiopwmio import PWMAudioOut as AudioOut
    except ImportError:
        pass  # not always supported by every board!

# Values for full/half power with PWM output
pwrFull = 65535
pwrHalf = 32768
pwrOff = 0

# Set a common value for the necessary servo movement (0-N)
doorAngle = 110

# Configure NeoPixels (ring) for effects on A1
pixelPin = board.A1
pixelCount = 16
pixelRing = neopixel.NeoPixel(pixelPin, pixelCount, brightness=1, auto_write=False)
pixelRing.fill(BLACK)
pixelRing.show()

# Configure a pushbutton on pin D0
btnTaunt = DigitalInOut(board.D0)
btnTaunt.switch_to_input(pull=Pull.DOWN)

# Configure a pushbutton on pin D1
btnOpen = DigitalInOut(board.D1)
btnOpen.switch_to_input(pull=Pull.DOWN)

# Configure a pushbutton on pin D2
btnStart = DigitalInOut(board.D2)
btnStart.switch_to_input(pull=Pull.DOWN)

# Create 2 PWMOut objects on D3/D4 (must use 50Hz)
pwm1 = PWMOut(board.D3, frequency=50)
pwm2 = PWMOut(board.D4, frequency=50)

# Configure a relay (for laser) on pin D7
relay = DigitalInOut(board.D7)
relay.direction = Direction.OUTPUT
relay.value = False

# Configure the capture-OK LED using full power on pin D9
ledOK = DigitalInOut(board.D9)
ledOK.direction = Direction.OUTPUT

# Configure the bar graph LED's using PWM
BAR_GRAPH = [
    {
        "NAME": "BG1",
        "ON": 3.0,
        "OFF": 1.0,
        "PREV_TIME": -1,
        "PIN": board.D10,
    },
    {
        "NAME": "BG2",
        "ON": 2.0,
        "OFF": 2.0,
        "PREV_TIME": -1,
        "PIN": board.D11,
    },
    {
        "NAME": "BG3",
        "ON": 1.0,
        "OFF": 3.0,
        "PREV_TIME": -1,
        "PIN": board.D12,
    }
]
for led in BAR_GRAPH:
    led["PIN"] = PWMOut(led["PIN"], frequency=400, duty_cycle=0)

# Create the L/R servo objects
servoLeft = servo.Servo(pwm1, min_pulse = 750, max_pulse = 2500)
servoRight = servo.Servo(pwm2, min_pulse = 750, max_pulse = 2500)

# Configure the primary sound file to be played.
# See https://learn.adafruit.com/circuitpython-essentials/circuitpython-audio-out
trap_seq_wav = open("trap_sequence_22.wav", "rb")
trap_seq_sfx = WaveFile(trap_seq_wav)
taunt_seq_wav = open("trap_beeps_12.wav", "rb")
taunt_seq_sfx = WaveFile(taunt_seq_wav)
audio = AudioOut(board.A0)

# Turn off and reset the bar graph LED's
def bar_graph_off():
    for led in BAR_GRAPH:
        led["PIN"].duty_cycle = pwrOff
        led["PREV_TIME"] = -1

# Define a process for building up the bar graph on a loop
def idle_state():
    # Store the current time to refer to later.
    now = time.monotonic()

    for led in BAR_GRAPH:
        if led["PREV_TIME"] == -1:
            led["PREV_TIME"] = now

    for led in BAR_GRAPH:
        if led["PIN"].duty_cycle == pwrOff:
            if now >= led["PREV_TIME"] + led["OFF"]:
                led["PREV_TIME"] = now
                led["PIN"].duty_cycle = pwrFull
                print(led["NAME"], "ON")
        if led["PIN"].duty_cycle == pwrFull:
            if now >= led["PREV_TIME"] + led["ON"]:
                led["PREV_TIME"] = now
                led["PIN"].duty_cycle = pwrOff
                print(led["NAME"], "OFF")

# Just close the doors
def close_doors():
    for angle in range(0, doorAngle, 10): # Move X degrees, 10 degrees at a time.
        # Remember motors must move in opposing directions
        servoLeft.angle = angle
        servoRight.angle = doorAngle - angle
        time.sleep(0.01)
    print("Doors Closed")

# Just open the doors
def open_doors():
    for angle in range(0, doorAngle, 10): # Move X degrees, 10 degrees at a time.
        # Remember motors must move in opposing directions
        servoLeft.angle = doorAngle - angle
        servoRight.angle = angle
        time.sleep(0.01)
    print("Doors Opened")

# Steady blink with sound
def do_taunt_sequence():
    # Turn off all bar graph LED's
    bar_graph_off()

    # Turn on the full bar graph
    print("Bar Graph Full")
    for led in BAR_GRAPH:
        led["PIN"].duty_cycle = pwrFull

    # Turn on the NeoPixels solid white
    pixelRing.fill(WHITE)
    pixelRing.show()

    # Start the SFX
    try:
        audio.play(taunt_seq_sfx)
    except Exception:
        print("Could not play audio")

    # Blink the indicator 12 times
    for count in range(12):
        # Blink the Trap-OK indicator at a rate of ~0.5s
        print("Blink:", count)
        # We need this illuminated longer than we need it off
        ledOK.value = True
        time.sleep(0.41)
        # Turn off briefly, but hold that state until next cycle
        ledOK.value = False
        time.sleep(0.085)

    # Turn off all bar graph LED's
    bar_graph_off()

    # Turn off the NeoPixels
    pixelRing.fill(BLACK)
    pixelRing.show()

# Run the full trap sequence with audio and SFX
def open_trap_sequence():
    # Turn off all bar graph LED's
    bar_graph_off()

    # Start the SFX
    try:
        audio.play(trap_seq_sfx)
    except Exception:
        print("Could not play audio")

    while audio.playing:
        # Trigger the laser relay
        print("Laser Active")
        relay.value = True

        # Open the trap doors via servos
        print("Doors Opening")
        open_doors()

        # Wait for doors to open
        time.sleep(0.44)

        # Start with a green effect
        pixelRing.fill(GREEN)
        pixelRing.show()

        # Pause before "capture"
        time.sleep(3)

        # Flash the NeoPixels
        print("Strobe Start")
        for count in range(40):
            pixelRing.fill(BLACK)
            pixelRing.show()
            time.sleep(0.05)
            pixelRing.fill(WHITE)
            pixelRing.show()
            time.sleep(0.05)

        # Do the capture-complete sequence
        close_trap_sequence()

# End the sequence by shutting everything down
def close_trap_sequence():
    # Open the trap doors via servos
    print("Doors Closing")
    close_doors()

    print("Laser Deactivated")
    time.sleep(0.2)
    # Shut down the laser
    relay.value = False

    # Delay before turning off lights
    time.sleep(0.4)

    # Turn off the NeoPixels
    print("Pixels Off")
    pixelRing.fill(BLACK)
    pixelRing.show()

    # Build the bar graph left to right, quickly
    print("Bar Graph Build")
    time.sleep(0.1)
    BAR_GRAPH[0]["PIN"].duty_cycle = pwrFull
    time.sleep(0.3)
    BAR_GRAPH[1]["PIN"].duty_cycle = pwrFull
    time.sleep(0.3)
    BAR_GRAPH[2]["PIN"].duty_cycle = pwrFull
    time.sleep(0.1)

    # Blink the indicator 22 times
    for count in range(22):
        # Blink the Trap-OK indicator at a rate of ~0.325s
        print("Blink:", count)
        # We need this illuminated longer than we need it off
        ledOK.value = True
        time.sleep(0.22)
        # Turn off briefly, but hold that state until next cycle
        ledOK.value = False
        time.sleep(0.105)

    # Reset all indicator lights
    time.sleep(1)
    bar_graph_off()
    ledOK.value = False
    time.sleep(1)
    print("Trap Done")

# Make sure the door servos are set to their closed position.
close_doors()

# Start the main loop after booting
while True:
    time.sleep(0.1) # Pause for debounce

    if btnStart.value:
        print("Opening the trap, look away!")
        open_trap_sequence()
    elif btnTaunt.value:
        print("Here little gouhlie...")
        do_taunt_sequence()
    elif btnOpen.value:
        open_doors()
        time.sleep(1)
    else:
        idle_state()
