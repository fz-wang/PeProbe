#!/usr/bin/env/ python3

import os,sys
#准备好已封端的PDB文件，封端包括氨基端、羧基端、Linker端，
#更新，为了自动去计算各cap的电荷，在PDB中把想要参数化的残基ncaa放在最前面，且把连接的linker放到该残基的最后，然后放ACE和NME，且ncaa前四个原子按照常规的N_CA_C_O顺序，减少程序复杂度
#from time import sleep

res=sys.argv[1]
resp = res+'_resp'

def generate_opt():    #将已经过前处理的PDB进行优化，最终输出带有RESP电荷的mol2文件

    os.system(f'antechamber -i {res}.pdb -fi pdb -o {res}.gjf -fo gcrt -gk "# HF/6-31G* opt" -ch "{res}.chk"')
    #得到Gaussian输入文件
    print(f'\nFZ-wang reminds you: The Gaussian opt input file has been generated and now Running!!\n')

    os.system(f'g16 {res}.gjf && antechamber -i {res}.log -fi gout -o {res}.mol2 -fo mol2 ')
    #得到优化结构mol2
    print(f'\nFZ-wang reminds you: The optimized structure of {res}.pdb has been output to {res}.mol2 and needs to be further processed!!\n')

    os.system(f'antechamber -i {res}.mol2 -fi mol2 -o {resp}.gjf -fo gcrt -gk "# HF/6-31G*  SCF=Tight  Pop=MK  iop(6/33=2,  6/41=10, 6/42=15)" -ch "{resp}.chk"')
    #得到RESP电荷计算输入gjf文件
    print(f'\nFZ-wang reminds you: Gaussian RESP-calculation input file({resp}.gjf) for {res}.mol2 has already been generated by antechamber!!\n')

    os.system(f'g16 {resp}.gjf && antechamber -i {resp}.log -fi gout -o {resp}_atomtype.mol2 -fo mol2 -at amber -pf y -c resp')
    #得到带有RESP电荷的mol2文件
    print(f'\nFZ-wang reminds you: The optimized structure with RESP charge has been output to {resp}_atomtype.mol2 and needs to be further processed!!\n')

def identify_conj():    

    f_params = open(res+'_temp.params','r')
    params = f_params.readlines()
    S_conjugations = []

    for line in params:    #得到硫原子的PDB名称
        if line[0:4] == 'ATOM' and 'S' in line:
            S_atom = line[5:9].strip()

    for line in params:
        if line[0:4] == 'BOND' and 'S' in line:
            S_bond = list(filter(None,line.replace('\n','').split(' ')))

            S_bond.remove(S_atom)
            S_bond.remove('BOND')
            S_conjugations.append(S_bond[0])
    #得到与硫原子相连的另外两个原子的信息

    conj1,conj2 = S_conjugations[0],S_conjugations[1]
    greek_alphabet = ['A', 'B', 'G', 'D', 'E', 'Z', 'T', 'I', 'K', 'L', 'M', 'N', 'X', 'O', 'P', 'R', 'S', 'U', 'P', 'C']
    conj1_order,conj2_order = greek_alphabet.index(conj1[1]),greek_alphabet.index(conj2[1])
    S_real_conj,S_bond = (conj1,conj2) if conj1_order<conj2_order else (conj2,conj1)

    H1,H2,H3 = f'H{S_bond[1:]}1',f'H{S_bond[1:]}2',f'H{S_bond[1:]}3'
    return S_real_conj,(S_atom,S_bond,H1,H2,H3)
    #判断NCAA中直接连接硫原子的是哪个原子，返回值中第一个值为NCAA末端CONNECT原子，第二个元组为Cys上硫原子及其相连的甲基

def substitute_mol2():    #将mol2中原子名称变为PDB中的名称，方便后续rtp文件信息的整理

    f_pdb = open(f'{res}.pdb','r')
    f_mol2 = open(f'{resp}_atomtype.mol2','r')
    pdb = f_pdb.readlines()

    #去掉pdb里面的空行
    for atom in pdb:
        if not bool(atom.strip()):
            pdb.remove(atom)
    
    pdb_atomtype = [line[12:16].strip() for line in pdb]
    #得到PDB中的原子类型

    mol2_atomtype = [j if j[0].isalpha() else j[1:]+j[0] for j in pdb_atomtype ]  #转换依据是，pdb中原子类型一般序号在前面，如1HZ，而mol2序号在后面，如HZ1
    #得到要写入到mol2中的原子类型

    mol2 = f_mol2.readlines()

    start = mol2.index('@<TRIPOS>ATOM\n') 
    end = mol2.index('@<TRIPOS>BOND\n') 
    #索引出__原子__所在的行

    assert len(pdb_atomtype) == end - start -1

    for i in range(start+1,end):
        head = mol2[i][0:8]   #原子类型前为序号
        tail = mol2[i][13:]   #原子类型后为坐标及其它信息

        middle = mol2_atomtype[i-start-1]
        total = f'{head}{middle:<4}{tail}'
        #写好更新的原子类型

        mol2[i] = total
        #更新mol2文件列表
    
    f_mol2_new = open(f'{resp}.mol2','w')
    for i in mol2:
        f_mol2_new.write(i)

def calculate_capcharge():    #计算三个封端的电荷信息，方便后续将之加到对应的原子上
    f_mol2 = open(f'{resp}.mol2','r')
    mol2 = f_mol2.readlines()
    
    end = mol2.index('@<TRIPOS>BOND\n') 
    start = mol2.index('@<TRIPOS>ATOM\n')

    linker_cap,ace_cap,nme_cap = 0,0,0

    for i in range(1+start,7+start):    #ACE_cap
        lis = list(filter(None,mol2[i].replace('\n','').split(' ')))
        ace_cap += eval(lis[-1])
    
    for j in range(7+start,13+start):    #NME_cap
        lis = list(filter(None,mol2[j].replace('\n','').split(' ')))
        nme_cap += eval(lis[-1])

    for k in range(start+1,end):    #Linker_cap
        lis = list(filter(None,mol2[k].replace('\n','').split(' ')))
        if lis[1] in ignore_atoms:
            linker_cap += eval(lis[-1])


    linker_cap,ace_cap,nme_cap = round(linker_cap,6),round(ace_cap,6),round(nme_cap,6)
    
    charge_info = open(f'{res}_cap.charge','w')
    charge_info.write(f'linker_cap:{linker_cap}\n')
    print(f'Sum charge of -S-CH3: {linker_cap}')
    charge_info.write(f'ace_cap:{ace_cap}\n')
    print(f'Sum charge of ACE: {ace_cap}')
    charge_info.write(f'nme_cap:{nme_cap}\n')
    print(f'Sum charge of NME: {nme_cap}')


    #增加功能：自动将cap残基总电荷加到对应原子上

    #N端与ACE相加
    N_ncaa_line = mol2[start+13]    #ACE、NME后pdb中NCAA的第一个原子是N
    N_ncaa = list(filter(None,N_ncaa_line.replace('\n','').split(' ')))
    if N_ncaa[1] == 'N':
        print(f'Detect N-termini, with original charge {N_ncaa[-1]}')
        
        new_N_charge = round(eval(N_ncaa_line[-10:-1]) + ace_cap,6)
        mol2[start+13] = N_ncaa_line.replace(N_ncaa_line[-10:-1],str(new_N_charge),1)
        
        print(f'Update N-termini charge with new value {mol2[start+13][-10:-1]}')
    else:
        raise Exception("Please check your PDB input, ensure N-CA-C-O order.")

    #C端与NME相加
    C_ncaa_line = mol2[start+15]
    C_ncaa = list(filter(None,C_ncaa_line.replace('\n','').split(' ')))
    if C_ncaa[1] == 'C':
        print(f'Detect C-termini, with original charge {C_ncaa[-1]}')
        
        new_C_charge = round(eval(C_ncaa_line[-10:-1]) + nme_cap,6)
        mol2[start+15] = C_ncaa_line.replace(C_ncaa_line[-10:-1],str(new_C_charge),1)
        
        print(f'Update C-termini charge with new value {mol2[start+15][-10:-1]}')
    else:
        raise Exception("Please check your PDB input, ensure N-CA-C-O order.")

    #遍历以找到侧链末端连接原子，并与linker相加
    for j in range(start+1,end):
        atom_ncaa = list(filter(None,mol2[j].replace('\n','').split(' ')))
        if atom_ncaa[1] == S_conj:
            linker_atom = eval(atom_ncaa[0])
            conjugation_ncaa_line = mol2[start+linker_atom]
            break
    
    conjugation_ncaa = list(filter(None,conjugation_ncaa_line.replace('\n','').split(' ')))
    assert conjugation_ncaa[1] == S_conj
    print(f'Detect linker-termini, with original charge {conjugation_ncaa[-1]}')
        
    new_conjugation_charge = round(eval(conjugation_ncaa_line[-10:-1]) + linker_cap,6)
    mol2[start+linker_atom] = conjugation_ncaa_line.replace(conjugation_ncaa_line[-10:-1],str(new_conjugation_charge),1)
    print(f'Update linker-termini charge with new value {mol2[start+linker_atom][-10:-1]}')

    #已经更新好了mol2，确保一下其电荷正确，理论上来说侧链均为共价连接的话，总电荷都为0|倘若后续出现例外再额外加判断条件
    #判断其电荷是否为0并将其写入新文件
    total_charge = 0
    for l in range(start+13,end):
        lis = list(filter(None,mol2[l].replace('\n','').split(' ')))
        if lis[1] not in ignore_atoms:
            total_charge += eval(lis[-1])
    
    if total_charge < 0.001:
        print(f'Total charge of the ncaa is {total_charge}(which approximates ZERO), now write the updated mol2 file!')
        recharge_mol2 = open(f'{resp}_recharge.mol2','w')
        for line in mol2:
            recharge_mol2.write(line)
    else:
        raise Exception(f'Total charge of the ncaa is {total_charge}, please check!')

def generate_top():    #生成GROMAC风格的top文件，以进一步生成rtp文件
    
    os.system(f'parmchk2 -i {resp}_recharge.mol2 -f mol2 -o {resp}.mod')
    #得到mod文件

    leapin=open('leap.in','w+')
    leapin.write(f'source leaprc.ff99SBildn \nloadamberparams {resp}.mod \nmol=loadmol2 {resp}.mol2 \ncheck mol \nsaveamberparm mol {resp}.prm {resp}.crd \nquit')
    leapin.close()
    #生成leapin文件

    os.system(f'tleap -f leap.in && rm leap.in')
    #调用tleap，删除leapin文件

    os.system(f'acpype -p {resp}.prm -x {resp}.crd -d')
    #得拓扑
    print(f'\nFZ-wang reminds you: The GROMACS top file of the whole system you input has been generated by leap&ACPYPE!!\n')

    os.system(f'rm qout QOUT punch md.mdp leap.log esout em.mdp')
    os.system(f'mv MOL_GMX.gro {resp}.gro')
    os.system(f'mv MOL_GMX.top {resp}.top')

def generate_rtp():    #将ACPYPE转出的top进一步整理为残基拓扑rtp格式
    f_top = open(f'{resp}.top','r')
    top = f_top.readlines()

    start_atom = top.index('[ atoms ]\n') + 2  #跳过[ atoms ]行和下一行注释
    start_bond = top.index('[ bonds ]\n') + 2  #同理
    end_atom = top.index('[ bonds ]\n') - 1 
    end_bond = top.index('[ pairs ]\n') - 1

    rtp_list = []
    rtp_list.append(f'[ {res} ]\n')  #残基条目
    rtp_list.append(' [ atoms ]\n')  #atoms

    all_real_atom = []  #收集ncaa中所有实原子，用于bond项的判断
    #非real-atom即那些不应该被包含在rtp和params中的原子，包括ACE、NME和linker(-S-CH3)

    for i in range(start_atom,end_atom):
        line = top[i]
        atom = list(filter(None,line.replace('\n','').split(' ')))
        if eval(atom[0]) < 13:    #第0位是原子序数
            continue
        pdb_name,atom_type,charge,num = atom[4],atom[1],atom[6],eval(atom[0])-12
        if pdb_name not in ignore_atoms:
            all_real_atom.append(pdb_name)
        rtp_list.append(f'    {pdb_name:>4}   {atom_type:>2}    {charge:>9}    {num:>2}\n')

    rtp_list.append(' [ bonds ]\n')

    for j in range(start_bond,end_bond):
        line = top[j]
        bond = list(filter(None,line.replace('\n','').split(' ')))
        if eval(bond[0]) < 13 or eval(bond[1]) < 13:
            continue
        rtp_list.append(f'    {bond[-3]:>4}   {bond[-1]:<4}  \n')

    rtp_list.append(f'    {"-C":>4}   {"N":<4}  \n')
    rtp_list.append(' [ impropers ]\n')
    rtp_list.append('    -C    CA     N     H\n    CA    +N     C     O\n')

    f_rtp = open(f'{res}.rtp','w')
    for line in rtp_list:
        f_rtp.write(line)

def main():

    generate_opt()

    S_conj,ignore_atoms = identify_conj()
    #鉴定出硫原子共价连接的原子S_conj，以及Cys上与硫原子连接的碳原子S_bond

    substitute_mol2()
    #得到RESP电荷、PDB原子类型的mol2文件
    print(f'\nFZ-wang reminds you: The atom types in .mol2 file have been substituted with which in PDB, for they can be more easily read and match the pdb2gmx/molfile_to_params/... applications!!\n')

    calculate_capcharge()
    #得到RESP电荷、PDB原子类型、修正电荷的mol2文件
    print(f'\nFZ-wang reminds you: The charges of N/C/{S_conj} atoms have been recalculated, to ensure the total charge of this NCAA equals to ZERO!!\n')
    
    generate_top()

    generate_rtp()
    print(f'\nFZ-wang reminds you: The top file has been processed and we generate the .rtp file for this NCAA, \
        which can be directly used in GROMACS!!\n')
    
    pass #Rosetta params
    print(f'\nFZ-wang reminds you: The param files of this NCAA used for Rosetta & Gromacs have been generated. \
        Have a cup of Latte and wish a good day!!\n')

if __name__ == '__main__':
    #main()
    #generate_opt()
    S_conj,ignore_atoms = identify_conj()

    generate_rtp()