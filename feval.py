import sys
import os
import glob
import h5py
import numpy as np
import re
import subprocess
import xml.etree.ElementTree as ElementTree
import math
import time
import logging

# Setting up logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] - %(message)s', filename='app.log', filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def main(argv):

    global no_of_real_variables

    # Read problem_name
    problem_name = fileread('problem_name.out')

    # Check for environment variables and set settings_file
    optimization_path = os.getenv('UNIFIED_OPTIMIZATION_PATH')
    optimization_time = os.getenv('UNIFIED_OPTIMIZATION_TIMENOW')

    if not optimization_path or not optimization_time:
        logging.error("Required environment variables UNIFIED_OPTIMIZATION_PATH or UNIFIED_OPTIMIZATION_TIMENOW are not set!")
        return

    settings_file = f"{optimization_path}/{optimization_time}_dataspace.h5"

    try:
        with h5py.File(settings_file, 'r') as f:
            no_of_objectives = f['optimization/number of objectives'][()]
            no_of_constraints = f['optimization/number of constraints'][()]
            no_of_real_variables = f['optimization/number of real variables'][()]
    except Exception as e:
        logging.error(f"Error opening or reading the file '{settings_file}': {e}")
        return

    try:
        infile = sys.argv[1]  # decision variables each variable is its own line
        x = np.genfromtxt(infile).astype(float)
    except IndexError:
        logging.error("No input file provided as an argument!")
        return
    except OSError:
        logging.error(f"Unable to open the file '{infile}'!")
        return
    except ValueError:
        logging.error(f"The content of the file '{infile}' is not in the expected format!")
        return

    outfile = sys.argv[2]  # OBJ and constraints

    fun = []
    if no_of_objectives > 0:
        fun = calc_functions(x, problem_name)

    if np.any(fun):
        np.savetxt(outfile, fun)


def calc_functions(x, problem_name):

    input_files = []
    input_files.append(glob.glob('./*.xml')[0])
    tree = ElementTree.parse(input_files[0])
    root = tree.getroot()
    for efile in root.iter('File'):
        if efile.get('name').find('.xml') > -1:
            input_files.append(efile.get('name'))

    second_per_year = 365*24*3600

    switch_time = x[0]*second_per_year
    table_coordinates = '{-1e11, 0, ' + str(switch_time) + ', 1e11 }'
    table_values = '{ ' + '0' + ', ' + str(x[1]) + ', ' + str(x[2]) + ', ' + str(x[2]) + '}'

    well_control_found = False
    i = -1
    while not well_control_found:
        i = i + 1
        tree = ElementTree.parse(input_files[i])
        root = tree.getroot()

        for elem in root.iter('WellControls'):
            if elem.get('name') == 'wellControls1':
                if 'targetTotalRateTableName' in elem.attrib:
                    for table in root.iter('TableFunction'):
                        if table.get('name') == elem.get('targetTotalRateTableName'):
                            table.set('coordinates', table_coordinates)
                            table.set('values', table_values)
                            tree.write(input_files[i])
                            well_control_found = True
                            break
                    if well_control_found:
                        break

    logging.info("Initial Variables Read")

    obj = []
    constr = []

    if well_control_found:
        logging.info("Simulation Run Started")
        


        
        command = os.getenv('UNIFIED_OPTIMIZATION_GEOS') + ' -i ' + input_files[0] + ' -x 8 -y 8 -z 1 >./output_geos.out'
        logging.info(command)
        os.system(command)

        match_number = re.compile('[-+]?\ *[0-9]+\.?[0-9]*(?:[Ee]\ *[-+]?\ *[0-9]+)?')
            # Open the output file for writing
        #     with open('./output_geos.out', 'w') as f_out, open('./errors_geos.out', 'w') as f_err:
        #         # Use subprocess.Popen to execute the command and capture the output in real-time
        #         with subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
        #             for line in process.stdout:
        #                 # Write the output to the output file in real-time
        #                 f_out.write(line)
        
        #             for line in process.stderr:
        #                 # Write the errors to the error file in real-time
        #                 f_err.write(line)
        
        #     # Check the return code after the process has completed
        #     return_code = process.returncode
        #     if return_code != 0:
        #         logging.error(f"Error executing system command. Return code: {return_code}")

        # except Exception as e:
        #     logging.error(f"Unexpected error: {e}")
        #     return []


        #try:
            #ret_val = os.system(os.getenv('UNIFIED_OPTIMIZATION_GEOS') + ' -i ' + input_files[0] + ' -x 8 -y 8 -z 1 ' + '>./output_geos.out')
            #command = os.getenv('UNIFIED_OPTIMIZATION_GEOS') + ' -i ' + input_files[0] + ' -x 8 -y 8 -z 1'
            #logging.info(command)

            #result = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Write output and errors to their respective files
            #with open('./output_geos.out', 'w') as f_out:
               # f_out.write(result.stdout)

            #with open('./errors_geos.out', 'w') as f_err:
                #f_err.write(result.stderr)

            # Check the return code
            #if result.returncode != 0:
                #logging.error(f"Error executing system command. Return code: {result.returncode}")
                #logging.error(f"Error message: {result.stderr.decode('utf-8')}")
                #return []
        #except Exception as e:
            #logging.error(f"Unexpected error: {e}")
            #return []


        try:
            with open('./output_geos.out', 'r') as outgeosf:
                logging.info("Output File Read")
                BHP = 0  # Initialize BHP 
                for line in outgeosf:
                    if 'BHP' in line:
                        final_list = [float(x) for x in re.findall(match_number, line)]
                        if final_list:
                            BHP = max(BHP, final_list[0])
                    if 'Dissolved component mass' in line:
                        final_list = [float(x) for x in re.findall(match_number, line)]
                        total_mass = final_list[0] + final_list[2]

                logging.info(BHP)
                logging.info(abs(60e9 - total_mass))

                obj.append(BHP)
                obj.append(abs(60e9 - total_mass))
                logging.info("Objective and constraint well appended")
        except Exception as e:
            logging.error(f"An unexpected error occurred while reading './output_geos.out': {e}")
            return ""

    return (np.array(np.append(obj, constr)))


def fileread(filename):
    try:
        with open(filename, 'r') as f:
            filecontent = f.read()
        return filecontent
    except FileNotFoundError:
        logging.error(f"File '{filename}' not found!")
        return ""
    except IOError:
        logging.error(f"Unable to read the file '{filename}'!")
        return ""
    except Exception as e:
        logging.error(f"An unexpected error occurred while reading '{filename}': {e}")
        return ""


if __name__ == '__main__':
    main(sys.argv[1:])
