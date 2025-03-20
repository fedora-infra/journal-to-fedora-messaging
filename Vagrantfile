# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.hostmanager.enabled = true
  config.hostmanager.manage_host = true
  config.hostmanager.manage_guest = true

  config.vm.define "journal-to-fedora-messaging" do |journal-to-fedora-messaging|
    journal-to-fedora-messaging.vm.box_url = "https://download.fedoraproject.org/pub/fedora/linux/releases/38/Cloud/x86_64/images/Fedora-Cloud-Base-Vagrant-38-1.6.x86_64.vagrant-libvirt.box"
    journal-to-fedora-messaging.vm.box = "f38-cloud-libvirt"
    journal-to-fedora-messaging.vm.hostname = "journal-to-fedora-messaging.tinystage.test"

    journal-to-fedora-messaging.vm.synced_folder '.', '/vagrant', disabled: true
    journal-to-fedora-messaging.vm.synced_folder ".", "/home/vagrant/journal-to-fedora-messaging", type: "sshfs"


    journal-to-fedora-messaging.vm.provider :libvirt do |libvirt|
      libvirt.cpus = 2
      libvirt.memory = 2048
    end

    journal-to-fedora-messaging.vm.provision "ansible" do |ansible|
      ansible.playbook = "devel/ansible/playbook.yml"
      ansible.config_file = "devel/ansible/ansible.cfg"
      ansible.verbose = true
    end
  end
end
