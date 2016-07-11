import ctypes
import socket
import struct
import sys
from threading import Timer
import threading


#server_host_name = '192.168.1.6'
server_host_name = socket.gethostname()
server_port = 7735
file_name = 'Test.pdf'
N = 10
MSS = 1000
TO=0.5
data_pack=21845
ack_pack=43690
acktype='I h h'
ack_format = struct.Struct(acktype)
lock = threading.Lock()


def cal_checksum(data):
    checksum = 0
    for i in range(0, len(data), 2):
        msg = str(data)
        word = ord(msg[i]) + (ord(msg[i+1]) << 8)
        carry = checksum + word
        checksum = (carry & 0xffff)+(carry >> 16)
    return (~ checksum) & 0xffff

def getdatafromfile(file_name):
    Buf=[]
    global MSS
    with  open(file_name, 'rb') as f:
        while True:
            data = f.read(MSS)
            if (len(data)<=0):
                break
            Buf.append(data)           
    return Buf

def sock_init():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    server_address = ( server_host_name, 7735)
    #server_address = ('localhost' , 7735)
    return sock, server_address
 

class WinBlock():
    def __init__(self, seqnum, data):
        self.data = data
        self.ackflag = False
        self.seq_num=seqnum
        
        

class Window():
    
    def __init__(self, sock, serv_add, file_content, win_size, max_seq, MMS, timeout):
        global TO
        self.sock = sock
        self.server_address = serv_add
        self.max_seq=max_seq
        self.win_timer = Timer(TO,self.resend_handler)
        self.buf = []
        self.flag_timeout = False
        self.flag_timer_started=False
        self.send_flag = True
        self.cur_seq = 0
        self.left_ptr=0;
        self.temp_index=self.left_ptr
        index=0;
        
        for data_chunk in file_content:
            seq_num = index%(max_seq)
            block = WinBlock(seq_num,data_chunk)
            self.buf.append(block)
            index+=1
        
        self.right_ptr=win_size-1
        if(len(file_content)-1<self.right_ptr):
            self.right_ptr=len(file_content)-1
            
    def start_transmission(self):
        global TO, lock
        threading.Thread(target=self.ack_receiver).start()
        self.temp_index = self.left_ptr
        while True:
            #print ("Left and right and Temp: ", self.left_ptr, ",",self.right_ptr,",",self.temp_index)
            if(self.temp_index<=self.right_ptr):
                if(self.flag_timeout==False):
                    #print("Sending packet: ", self.buf[self.temp_index].seq_num)
                    self.send_packet(self.temp_index)
                    if(self.flag_timer_started==False):
                        #print ("Timer Started")
                        self.win_timer = Timer(TO,self.resend_handler)
                        self.win_timer.start()
                        self.flag_timer_started=True
                    self.temp_index+=1
                    #print ("Temp", self.temp_index)
            if(self.temp_index>=len(self.buf)):
                break;
        
        return
    
    
                
    def ack_receiver(self):
        global ack_format
        global N
        global TO
        #sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #sock.bind((socket.gethostname(),8000))
        while True:
            try:
                ack,addr = self.sock.recvfrom(ack_format.size)
                tup = ack_format.unpack_from(ack,0)
                recvd_seq_ack = tup[0]
                seq_num_from_index = self.left_ptr%(self.max_seq)
                #if(((seq_num_from_index==N) and recvd_seq_ack==0) or (recvd_seq_ack+1==seq_num_from_index)):
                #   return
                actual_index = self.left_ptr+(recvd_seq_ack-seq_num_from_index)
                #print("Received Ack and index ",recvd_seq_ack,",",actual_index)
                if(actual_index>=self.left_ptr and actual_index<=self.right_ptr):
                #if(actual_index==self.left_ptr):
                    self.win_timer.cancel()
                    self.win_timer = Timer(TO,self.resend_handler)
                    self.win_timer.start()
                    #print("Timer started and stopped")
                    if(actual_index==len(self.buf)-1 or self.temp_index>=len(self.buf)):
                        self.win_timer.cancel()
                        return
                    self.left_ptr=actual_index+1
                    self.temp_index=self.left_ptr
                    #print ("Temp", self.temp_index)
                    if(self.left_ptr+N-1<len(self.buf)):
                        self.right_ptr=self.left_ptr+N-1
                    else:
                        self.right_ptr=len(self.buf)-1 
                '''print ("temp, left and right index:",self.buf[self.temp_index].seq_num,",",
                        self.buf[self.left_ptr].seq_num,",",self.buf[self.right_ptr].seq_num)   
                print ("temp, left and right index:",self.temp_index,",",
                        self.left_ptr,",",self.right_ptr)  '''     
            except:
                continue
            
            
        
    def resend_handler(self):
        global TO
        global N
        self.flag_timer_started=False
        self.win_timer.cancel()
        print ("Timeout, sequence number = ",(self.left_ptr)%(N+1))
        self.flag_timeout=True
        right = self.right_ptr
        
        self.temp_index=self.left_ptr
        while(self.temp_index<=right):
            self.send_packet(self.temp_index)
            if(self.flag_timer_started==False):
                self.win_timer = Timer(TO,self.resend_handler)
                self.win_timer.start()
                self.flag_timer_started=True
            self.temp_index+=1
            #print ("RETemp", self.temp_index)
        self.flag_timeout=False
        
        
    def send_packet(self,index):
        global datatype
        global data_format
        datatype='I H H '+str(len(self.buf[index].data))+'s'
        data_format = struct.Struct(datatype)
        values = (self.buf[index].seq_num,cal_checksum(self.buf[index].data),data_pack, self.buf[index].data)
        pkt = ctypes.create_string_buffer(data_format.size)
        data_format.pack_into(pkt, 0, *values)
        self.sock.sendto(pkt,self.server_address)
        

def rdt_send():
    sock, server_address = sock_init()
    buf = getdatafromfile(file_name)
    
    win = Window(sock,server_address,buf,N,N+1,MSS,TO)
    win.start_transmission()
    print("Upload completed")
    sys.exit()
    
rdt_send()