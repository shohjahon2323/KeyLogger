# CYBER RANGE LAB 1: Insecure Deserialization
# Vulnerable Ruby Code

require 'yaml'

class UserProfile
  attr_accessor :username, :is_admin

  def initialize(username)
    @username = username
    @is_admin = false
  end

  def print_status
    if @is_admin
      puts "[+] Welcome Administrator: #{@username}. Flag: CTF{ruby_deserialization_master}"
    else
      puts "[-] Welcome user: #{@username}. Access Denied."
    end
  end
end

puts "[*] TryHackMe Lab: Ruby Deserialization"
puts "Enter serialized YAML data:"
yaml_data = gets.chomp

begin
  # VULNERABILITY: Unsafe YAML loading allows object injection
  user = YAML.load(yaml_data)
  user.print_status
rescue => e
  puts "Error: #{e.message}"
end
