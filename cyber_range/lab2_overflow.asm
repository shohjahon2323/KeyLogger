global _start

section .data
    msg db 'Cyber Range Lab: Buffer Overflow Challenge', 0xA
    len equ $ - msg
    flag db 'CTF{assembly_shellcode_executed}', 0

section .text
_start:
    ; Print welcome message
    mov eax, 4
    mov ebx, 1
    mov ecx, msg
    mov edx, len
    int 0x80

    ; Call vulnerable function
    call vulnerable_func

    ; Exit
    mov eax, 1
    xor ebx, ebx
    int 0x80

vulnerable_func:
    ; VULNERABILITY: No bounds checking on input buffer
    push ebp
    mov ebp, esp
    sub esp, 64 ; 64 byte buffer

    ; Read input
    mov eax, 3
    mov ebx, 0
    lea ecx, [ebp-64]
    mov edx, 128 ; Reading 128 bytes into a 64 byte buffer! OVERFLOW!
    int 0x80

    leave
    ret
