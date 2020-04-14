from sys import *
import re
import readelf
path_des_file = argv[1]
template_file = argv[2]
execl_file = argv[3]
    
#********************************************************************************************
# Function: load symbols from ELF file
#********************************************************************************************
import logging
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.descriptions import (
    describe_symbol_type,
    describe_symbol_shndx)

logger = logging.getLogger(__name__)
 
def load_symbols_elf(filename):
    """ Load the symbol tables contained in the file
    """
    f = open(filename, 'rb')
 
    elffile = ELFFile(f)
 
    symbols = []
 
    for section in elffile.iter_sections():
        if not isinstance(section, SymbolTableSection):
            continue
 
        if section['sh_entsize'] == 0:
            logger.warn("Symbol table {} has a sh_entsize of zero.".format(section.name))
 
            continue
 
        logger.info("Symbol table {} contains {} entries.".format(section.name, section.num_symbols()))
 
        for _, symbol in enumerate(section.iter_symbols()):
            if describe_symbol_shndx(symbol['st_shndx']) != "UND" and \
                describe_symbol_type(symbol['st_info']['type']) == "OBJECT":
                symbols.append((symbol['st_value'], symbol['st_size'], symbol.name))
 
    f.close()
 
    symbols_by_addr = {
        addr : (name, size, True)
            for addr, size, name in symbols
    }
 
    return symbols_by_addr
#********************************************************************************************
# End of Function
#********************************************************************************************

#********************************************************************************************
# Function: write measurement elements into a2l file
#********************************************************************************************
def Meas_A2L_Write(debug_file, a2l_file, prototype_dic):
    a2l_file.write('/begin MEASUREMENT'+'\n')
    a2l_file.write(prototype_dic.get('Display_Identifier')+'\n')
    a2l_file.write('"'+prototype_dic.get('LongIdentifier')+'"'+'\n')
    variable_type = prototype_dic.get('Datatype')
    if variable_type.find('ARRAY') >= 0:
        (variable_datatype, variable_array) = variable_type.split('_')
    else:
        variable_datatype = variable_type
        variable_array = 'VALUE'
    a2l_file.write(variable_datatype +'\n')
    a2l_file.write(prototype_dic.get('Conversion')+'\n')
    a2l_file.write(str(round(float(prototype_dic.get('Resolution'))))+'\n')
    a2l_file.write(prototype_dic.get('Accuracy')+'\n')
    a2l_file.write(prototype_dic.get('LowerLimit')+'\n')
    a2l_file.write(prototype_dic.get('UpperLimit')+'\n')
    a2l_file.write('FORMAT '+prototype_dic.get('FORMAT')+'\n')
    temp = prototype_dic.get('Display_Identifier')
    if temp.find('.') > 0:
        (variable_ref, variable_name) = temp.split('.')
    else:
        variable_name = temp
        variable_ref = ''
    variable_type = variable_array
    address = Get_Address_From_Debug_File(debug_file, variable_name, variable_type, variable_ref)
    if variable_type == 'ARRAY':
        a2l_file.write('ARRAY_SIZE ' + str(round(float(prototype_dic.get('ArraySize'))))+'\n')
    a2l_file.write(r'ECU_ADDRESS ')
    a2l_file.write(str(address))
    a2l_file.write('\n')
    a2l_file.write('/end MEASUREMENT'+'\n'+'\n')

#********************************************************************************************
# End of Function
#********************************************************************************************

#********************************************************************************************
# Function: write characteristic elements into a2l file
#********************************************************************************************
def Cali_A2L_Write(debug_file, a2l_file, prototype_dic):
    a2l_file.write('/begin CHARACTERISTIC'+'\n')
    a2l_file.write(prototype_dic.get('Display_Identifier')+'\n')
    a2l_file.write('"'+prototype_dic.get('LongIdentifier')+'"'+'\n')
    a2l_file.write(prototype_dic.get('Type')+'\n')
    variable_name = prototype_dic.get('Display_Identifier')
    variable_type = prototype_dic.get('Type')
    variable_ref = prototype_dic.get('DataStruct')
    address = Get_Address_From_Debug_File(debug_file, variable_name, variable_type, variable_ref)
    a2l_file.write(r'ECU_ADDRESS '+ address +'\n')
    a2l_file.write(prototype_dic.get('Deposit')+'\n')
    a2l_file.write(prototype_dic.get('Maxdiff')+'\n')
    a2l_file.write(prototype_dic.get('Conversion')+'\n')
    a2l_file.write(prototype_dic.get('LowerLimit')+'\n')
    a2l_file.write(prototype_dic.get('UpperLimit')+'\n')
    a2l_file.write('FORMAT '+prototype_dic.get('FORMAT')+'\n')
    if variable_type == 'VAL_BLK':
        a2l_file.write('NUMBER '+str(round(float(prototype_dic.get('NUMBER'))))+'\n')
    a2l_file.write('/end CHARACTERISTIC'+'\n'+'\n')

#********************************************************************************************
# End of Function
#********************************************************************************************

#********************************************************************************************
# Function: write conversion(compu_method) into a2l file
#********************************************************************************************
def Conv_A2L_Write(debug_file, a2l_file, prototype_dic):
    a2l_file.write('/begin COMPU_METHOD'+'\n')
    a2l_file.write(prototype_dic.get('Display_Identifier')+'\n')
    a2l_file.write('"'+prototype_dic.get('LongIdentifier')+'"'+'\n')
    a2l_file.write(prototype_dic.get('ConversionType')+'\n')
    a2l_file.write('"'+prototype_dic.get('FORMAT')+'"'+'\n')
    if prototype_dic.get('Unit') == 'N/A'or'':
        a2l_file.write('"-"'+'\n')
    else:
        a2l_file.write('"'+prototype_dic.get('Unit')+'"'+'\n')
    a2l_file.write('COEFFS '+prototype_dic.get('COEFFS')+'\n')
    a2l_file.write('/end COMPU_METHOD'+'\n'+'\n')

#********************************************************************************************
# End of Function
#********************************************************************************************

#********************************************************************************************
# Function: get address value in debug file
#********************************************************************************************
def Get_Address_From_Debug_File(debug_file, variable_name, variable_type, variable_ref):
    # find address info in debug file
    file = open(debug_file, 'r')
    if variable_ref != '':
        # is a structer variable
        structer = variable_ref
        member = variable_name
        structer_find = False
        member_find = True
        structer_exist = False
        member_exist = False
        address_base_exist = False
        address_offset_exist = False
        for line in file.readlines():
            # find member firstly
            if member_find:
                if member_exist:
                    if line.find('DW_OP_plus_uconst') > 0:
                        temp = re.findall(r'[(](.*?)[)]', line.strip())
                        (val1, val2) = temp[0].split(' ')
                        address_offset = val2
                        # finish structer_find, start member_find
                        structer_find = True
                        member_find = False
                        address_offset_exist = True
                else:
                    if line.find(member + '\n') > 0:
                        # member exist, continue to find address offset
                        member_exist = True
            # start find structer
            if structer_find:
                if structer_exist:
                    if line.find('DW_OP_addr') > 0:
                        temp = re.findall(r'[(](.*?)[)]', line.strip())
                        (val1, val2) = temp[0].split(' ')
                        if val2.find('0x') == 0:
                            # Hex to Dec
                            address_base = eval(val2)
                        else:
                            # add 0x and change to Dec
                            val2 = '0x' + val2
                            address_base = eval(val2)
                        address_base_exist = True
                        break
                else:
                    if line.find(structer + '\n') > 0:
                        # structer exist, continue to find base address
                        structer_exist = True
        if structer_exist == False:
            print(structer + " not found!")
            exit()
        elif member_exist == False:
            print(member + " not found!")
            exit()
        elif address_offset_exist == False:
            print(member + " address info not found!")
            exit()
        elif address_base_exist == False:
            print(structer + " address info not found!")
            exit()
        else:
            # calculate address value
            temp1 = str(hex(int(address_base) + int(address_offset)))
            if len(temp1) < 10:
                index = 10 - len(temp1)
                zero = ['', '0', '00', '000', '0000', '00000']
                temp2 = list(temp1)
                temp2.insert(2, zero[index])
                temp3 = [str(i) for i in temp2]
                address = ''.join(temp3)
            else:
                address = temp1
    elif variable_type == 'VALUE' or 'VAL_BLK':
        # is a normal variable
        variable_exist = False
        address_exist = False
        for line in file.readlines():
            if variable_exist:
                if line.find('DW_OP_addr') > 0:
                    # get variable's address
                    temp = re.findall(r'[(](.*?)[)]', line.strip())
                    (val1, val2) = temp[0].split(' ')
                    address_exist = True
                    break
            else:
                if line.find(variable_name + '\n') > 0:
                    variable_exist = True
        if variable_exist == False:
            print(variable_name + " not found!")
            exit()
        elif address_exist == False:
            print(variable_name + " address info not found!")
            exit()
        else:
            if len(val2) < 8:
                index = 8 - len(val2)
                zero = ['', '0', '00', '000', '0000', '00000']
                temp = list(val2)
                temp.insert(2, zero[index])
                temp1 = [str(i) for i in temp]
                temp2 = ''.join(temp1)
                address = '0x' + temp2
            else:
                address = '0x' + val2
    file.close()
    if variable_ref != '':
        print(variable_ref + '.' + variable_name + ' address found in debug file: ' + address)
    else:
        print(variable_name + ' address found in debug file: ' + address)
    return address
#********************************************************************************************
# End of Function
#********************************************************************************************

#********************************************************************************************
# Function: write elements into a2l file
#********************************************************************************************
def Read_Elements_From_Execl_And_Write_Into_A2l(execl_sheet, debug_file, a2l_file, func_a2l_write):
    elem_para_list = []
    # get the type of elements prototype parameters
    for col in range(0, execl_sheet.ncols):
        if execl_sheet.cell_value(0,col):
            elem_para_list.append(execl_sheet.cell_value(0,col))
        else:
            break
    # get the value of every paramenter for each element prototype
    for row in range(1,execl_sheet.nrows):
        elem_para_val_list = []
        for col in range(0,execl_sheet.ncols):
            if execl_sheet.cell_value(0,col) != "":
                elem_para_val_list.append(str(execl_sheet.cell_value(row,col)))
            else:
                break
        elem_para_dict = dict(zip(elem_para_list,elem_para_val_list))
        func_a2l_write(debug_file, a2l_file, elem_para_dict)
#********************************************************************************************
# End of Function
#********************************************************************************************

#********************************************************************************************
# Find describe file, including ELF/ABS/AXF
#********************************************************************************************
print("************ Start Generate A2l file **************")
import os
des_file_counter = 0
for root, dirs, files in os.walk(path_des_file):
    for file in files:
        (filename, extension) = os.path.splitext(file)
        if(extension == '.axf'):
            des_file = os.path.join(path_des_file, file)
            des_file_counter = des_file_counter + 1
            break
    break
if des_file_counter == 0:
    print("ERROR: Describe file not found")
    print("Generate a2l file failed!!!")
    exit()
else:
    print('Describe file found: ' + des_file)

# open debug file
readelf.main(des_file, 'info')
#debug_file = open('debug_info.txt', 'r')
debug_file = 'debug_info.txt'
# read execl_file
import xlrd
execl_wb = xlrd.open_workbook(execl_file)

execl_wb_sheet_meas = execl_wb.sheet_by_name('Measurement')
meas_a2l_file = open('meas_temp.a2l', 'a+')
Read_Elements_From_Execl_And_Write_Into_A2l(execl_wb_sheet_meas,debug_file,meas_a2l_file,Meas_A2L_Write)
meas_a2l_file.close()

execl_wb_sheet_conv = execl_wb.sheet_by_name('Conversion')
conv_a2l_file = open('conv_temp.a2l', 'a+')
Read_Elements_From_Execl_And_Write_Into_A2l(execl_wb_sheet_conv,debug_file,conv_a2l_file,Conv_A2L_Write)
conv_a2l_file.close()

execl_wb_sheet_cali = execl_wb.sheet_by_name('Characteristic')
cali_a2l_file = open('cali_temp.a2l', 'a+')
Read_Elements_From_Execl_And_Write_Into_A2l(execl_wb_sheet_cali,debug_file,cali_a2l_file,Cali_A2L_Write)
cali_a2l_file.close()



input("Press <enter>")


