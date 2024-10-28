provider "aws" {
    region = "eu-west-1"
}

variable "node_size" {
    description = "Size of total nodes"
    default = 2
}

variable "nodes_intance_type" {
    description = "ec2 instance type of a leader and workers"
    default = "c5n.4xlarge"
}

variable "loadtest_dir_source" {
    default = "plan/"
}

variable "locust_plan_filename" {
    default = "locustfile.py"
}

variable "ssh_export_pem" {
    description = "Export private ssh key"
    type        = bool
    default     = true
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "vpc-for-locust"
  cidr = "10.0.0.0/16"

  azs             = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
  public_subnets  = ["10.0.101.0/24"]
  enable_dns_hostnames = true
  enable_dns_support   = true
}

module "loadtest" {

    source  = "marcosborges/loadtest-distribuited/aws"

    name = "aws-proxy-performance-test"
    nodes_size = var.node_size
    executor = "locust"
    region = "eu-west-1"
    

    # LEADER ENTRYPOINT
    loadtest_entrypoint = <<-EOT
        sudo yum update -y
        sudo yum install -y pcre2-devel.x86_64 python gcc python3-devel tzdata curl unzip bash htop
        
        export LOCUST_VERSION="2.15.1"
        sudo pip3 uninstall urllib3 --no-input
        sudo pip3 install urllib3==1.26.6 --no-input
        sudo pip3 install locust==$LOCUST_VERSION --no-input

        nohup locust \
            -f ${var.locust_plan_filename} \
            --web-port=8080 \
            --tags full_test_case \
            --expect-workers=${var.node_size} \
            --master > locust-leader.out 2>&1 &
    EOT

    # NODES ENTRYPOINT
    node_custom_entrypoint = <<-EOT
        sudo yum update -y
        sudo yum install -y pcre2-devel.x86_64 python gcc python3-devel tzdata curl unzip bash htop
        
        export LOCUST_VERSION="2.15.1"
        sudo pip3 uninstall urllib3 --no-input
        sudo pip3 install urllib3==1.26.6 --no-input
        sudo pip3 install locust==$LOCUST_VERSION --no-input
        nohup locust \
            -f ${var.locust_plan_filename} \
            --worker \
            --master-host={LEADER_IP} > locust-worker.out 2>&1 &
    EOT

    subnet_id = element(module.vpc.public_subnets,0)
    loadtest_dir_source = var.loadtest_dir_source
    locust_plan_filename = var.locust_plan_filename
    ssh_export_pem = var.ssh_export_pem

    leader_associate_public_ip_address = true
    nodes_associate_public_ip_address = true

    leader_monitoring = true
    nodes_monitoring = true

    ssh_cidr_ingress_blocks = ["0.0.0.0/0"]

    depends_on = [ module.vpc ]

}