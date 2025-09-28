from clockmmu import ClockMMU
from lrummu import LruMMU
from optimal import OptimalMMU
from randmmu import RandMMU
from collections import deque  # For efficient popleft in Optimal

import sys


def main():
    PAGE_OFFSET = 12  # page is 2^12 = 4KB

    ############################
    # Check input parameters   #
    ############################

    if (len(sys.argv) < 5):
        print("Usage: python memsim.py inputfile numberframes replacementmode debugmode")
        return

    input_file = sys.argv[1]

    try:
        with open(input_file, 'r') as file:
            # Read the trace file contents
            trace_contents = file.readlines()
    except FileNotFoundError:
        print(f"Input '{input_file}' could not be found")
        print("Usage: python memsim.py inputfile numberframes replacementmode debugmode")
        return

    frames = int(sys.argv[2])
    if frames < 1:
       print("Frame number must be at least 1\n")
       return

    replacement_mode = sys.argv[3]

    # Setup MMU based on replacement mode
    if replacement_mode == "rand":
        mmu = RandMMU(frames)
    elif replacement_mode == "lru":
        mmu = LruMMU(frames)
    elif replacement_mode == "clock":
        mmu = ClockMMU(frames)
    elif replacement_mode == "optimal":
        mmu = OptimalMMU(frames)
    else:
        print("Invalid replacement mode. Valid options are [rand, lru, esc], optimal")
        return

    debug_mode  = sys.argv[4]

    # Set debug mode
    if debug_mode == "debug":
        mmu.set_debug()
    elif debug_mode == "quiet":
        mmu.reset_debug()
    else:
        print("Invalid debug mode. Valid options are [debug, quiet]")
        return

    ############################################################
    # Main Loop: Process the addresses from the trace file     #
    ############################################################

    no_events = 0

    trace_list = []
    future_access = {} 

    # with open(input_file, 'r') as trace_file:
    for trace_line in trace_contents:
        trace_cmd = trace_line.strip().split(" ")
        logical_address = int(trace_cmd[0], 16)
        page_number = logical_address >>  PAGE_OFFSET
        trace_list.append((page_number, trace_cmd[1])) # (page number, R/W)

         
    # Build future_access ONLY for optimal, and ONLY after full trace is read
    if replacement_mode == "optimal":
        for i, (page_number, mode) in enumerate(trace_list):
            if page_number not in future_access:
                future_access[page_number] = deque()  # Use deque for O(1) popleft
            future_access[page_number].append(i)
    

    for i, (page_number, mode) in enumerate(trace_list):
        if mode not in ("R", "W"):
            print(f"Badly formatted file. Error on line {no_events + 1}")
            return
        # Process read or write
        if replacement_mode == "optimal":
            if mode == "R":
                mmu.read_memory(page_number, i, future_access)
            elif mode == "W":
                mmu.write_memory(page_number, i, future_access)
        else:     
            if mode == "R":
                mmu.read_memory(page_number)
            elif mode == "W":
                mmu.write_memory(page_number)

        no_events += 1



    # TODO: Print results
    print(f"total memory frames: {frames}")
    print(f"events in trace: {no_events}")
    print(f"total disk reads: {mmu.get_total_disk_reads()}")
    print(f"total disk writes: {mmu.get_total_disk_writes()}")
    print("page fault rate: ", end="")
    print("{0:.4f}".format(mmu.get_total_page_faults() / no_events))

if __name__ == "__main__":
    main()
                    
