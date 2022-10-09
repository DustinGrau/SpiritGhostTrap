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
import adafruit_dotstar
import audioio
import board
import time
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

# Configure the DotStar LED
dot_led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)

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
ledBar1 = PWMOut(board.D10, frequency=400, duty_cycle=0)
ledBar2 = PWMOut(board.D11, frequency=400, duty_cycle=0)
ledBar3 = PWMOut(board.D12, frequency=400, duty_cycle=0)
ledBar = [ledBar1, ledBar2, ledBar3]

# Configure the main white LED using PWM
ledWhite = PWMOut(board.D5, frequency=400, duty_cycle=0)

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

# Turn off all LED's
def reset_LEDs():
    # Turn off bar graph
    ledBar1.duty_cycle = pwrOff
    ledBar2.duty_cycle = pwrOff
    ledBar3.duty_cycle = pwrOff

    # Turn off the white LED
    ledWhite.duty_cycle = pwrOff

# Define a process for building up the bar graph on a loop
def idle_state():
    # Set the DotStar LED to green
    dot_led[0] = (0, 60, 0)

    # Set a constant sleep time
    sleepTime = 0.6

    # Build the bar graph left to right, repeat
    for led in range(0, 3):
        # On each increment of bar graph, check if buttons were pressed and exit
        if btnStart.value or btnTaunt.value or btnOpen.value:
            return
        print(led+1)
        ledBar[led].duty_cycle = pwrFull
        time.sleep(sleepTime)

        if led == 2:
            ledBar1.duty_cycle = pwrOff
            ledBar2.duty_cycle = pwrOff
            ledBar3.duty_cycle = pwrOff
            time.sleep(sleepTime)

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
    # Set the DotStar LED to blue
    dot_led[0] = (0, 0, 60)

    # Turn off all external LED's
    reset_LEDs()

    # Turn on the full bar graph
    print("Bar Graph Full")
    ledBar1.duty_cycle = pwrFull
    ledBar2.duty_cycle = pwrFull
    ledBar3.duty_cycle = pwrFull

    # Turn on the white LED
    ledWhite.duty_cycle = pwrFull

    # Start the SFX
    audio.play(taunt_seq_sfx)

    # Blink the indicator 12 times
    for count in range(0, 12):
        # Blink the Trap-OK indicator at a rate of ~0.5s
        print("Blink:", count)
        # We need this illuminated longer than we need it off
        ledOK.value = True
        time.sleep(0.41)
        # Turn off briefly, but hold that state until next cycle
        ledOK.value = False
        time.sleep(0.085)

    # Turn off all external LED's
    reset_LEDs()

# Run the full trap sequence with audio and SFX
def open_trap_sequence():
    # Set the DotStar LED to red
    dot_led[0] = (60, 0, 0)

    # Turn off all external LED's
    reset_LEDs()

    # Start the SFX
    audio.play(trap_seq_sfx)

    while audio.playing:
        # Trigger the laser relay
        print("Laser Active")
        relay.value = True

        # Open the trap doors via servos
        print("Doors Opening")
        open_doors()

        # Turn on the main lights
        print("Lights On")
        ledWhite.duty_cycle = pwrFull

        # Wait for the end sequence portion of the audio
        time.sleep(7.54)

        # Do the capture-complete sequence
        close_trap_sequence()

# End the sequence by shutting everything down
def close_trap_sequence():
    # Set the DotStar LED to blue
    dot_led[0] = (0, 0, 60)

    # Open the trap doors via servos
    print("Doors Closing")
    close_doors()

    print("Laser Deactivated")
    time.sleep(0.2)
    # Shut down the laser
    relay.value = False

    # Turn off the main lights
    time.sleep(0.4)
    print("Lights Off")
    ledWhite.duty_cycle = pwrOff

    # Build the bar graph left to right, quickly
    print("Bar Graph Build")
    time.sleep(0.1)
    ledBar1.duty_cycle = pwrFull
    time.sleep(0.3)
    ledBar2.duty_cycle = pwrFull
    time.sleep(0.3)
    ledBar3.duty_cycle = pwrFull
    time.sleep(0.1)

    # Blink the indicator 22 times
    for count in range(0, 22):
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
    ledBar1.duty_cycle = pwrOff
    ledBar2.duty_cycle = pwrOff
    ledBar3.duty_cycle = pwrOff
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
