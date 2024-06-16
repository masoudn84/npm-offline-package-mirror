import os
import subprocess
import logging
import json
import shutil

# Configure logging
logging.basicConfig(filename='publish_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Set your Nexus repository URL and authentication details
NEXUS_REPOSITORY_URL = 'http://example.com/repository/npm-private'
NEXUS_USER = 'your-nexus-username'
NEXUS_PASSWORD = 'your-nexus-password'
DOWNLOAD_DIR = 'downloaded_tgz'  # Directory to store downloaded tarballs

def is_package_directory(directory):
    """Check if a directory contains a package.json file."""
    return os.path.isfile(os.path.join(directory, 'package.json'))

def run_command(command, cwd=None):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(command, cwd=cwd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{command}' failed in directory '{cwd}'. Error: {e.stderr.decode('utf-8').strip()}")
        return None

def npm_pack(directory):
    """Run npm pack in the given directory and return the name of the created tarball."""
    output = run_command('npm pack', cwd=directory)
    if output:
        tarball_name = output.split('\n')[-1]
        return tarball_name
    return None

def npm_view_and_wget(directory):
    """Use npm view to get the tarball URL and download it with wget."""
    try:
        # Get package name and version from package.json
        with open(os.path.join(directory, 'package.json')) as f:
            package_info = json.load(f)
        package_name = package_info['name']
        package_version = package_info['version']

        # Get tarball URL using npm view
        result = run_command(f"npm view {package_name}@{package_version} dist.tarball")
        print("+++++++++++++++++"+result)
        if result:
            print("---------------------")
            tarball_url = result.strip()
            tarball_name = tarball_url.split('/')[-1]
            tarball_path = os.path.join(DOWNLOAD_DIR, tarball_name)
            # Download tarball using wget
            wget_command = f"wget -O {tarball_path} {tarball_url}"
            print("*******************"+wget_command)
            wget_result = run_command(wget_command)
            if wget_result is not None:
                return tarball_name

            cwd = os.getcwd()
            print("..............."+cwd)
            print(os.listdir())
            os.chdir(DOWNLOAD_DIR)
            print(os.listdir())
            #print("..............."+os.chdir(DOWNLOAD_DIR))
            print(os.listdir())
            os.system("npm publish " + tarball_name + " --registry=" +  NEXUS_REPOSITORY_URL)
            os.chdir(cwd)
    except Exception as e:
        logging.error(f"Error during npm view and wget in directory '{directory}': {str(e)}")
    return None

def npm_publish(directory, tarball_name):

    """Publish the tarball to Nexus repository using npm publish."""
    tarball_path = os.path.join(directory, tarball_name)
    publish_result = run_command(f'npm publish {tarball_path}', cwd=directory)
    if publish_result is None:
        logging.error(f"Failed to publish tarball '{tarball_name}' from directory '{directory}'")

def process_directory(directory, remaining_count):
    """Process a single directory: pack and publish if it's a valid npm package directory."""
    if is_package_directory(directory):
        print(f"Processing package in directory: {directory}")
        tarball_name = npm_pack(directory)
        if not tarball_name:
            print(f"npm pack failed for {directory}. Trying npm view and wget.")
            tarball_name = npm_view_and_wget(directory)
        if tarball_name:
            npm_publish(DOWNLOAD_DIR, tarball_name)
    print(f"Remaining directories: {remaining_count}")

def crawl_directories(root_directory):
    """Crawl through all subdirectories of the given root directory."""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    total_directories = sum([len(dirs) for _, dirs, _ in os.walk(root_directory)]) + 1  # Including root directory
    current_count = 0
    for subdir, _, _ in os.walk(root_directory):
        remaining_count = total_directories - current_count
        process_directory(subdir, remaining_count)
        current_count += 1
    print(f"Total directories processed: {current_count}")

if __name__ == "__main__":
    node_modules_dir = 'node_modules'  # Change this to the path of your node_modules directory
    crawl_directories(node_modules_dir)
    print("Done. Check publish_errors.log for any errors.")
