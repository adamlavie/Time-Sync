import json
import time
import docker

docker_client = docker.from_env()


def pull_image(name, tag=None, stream=None):
    for line in docker_client.pull(name, tag=tag, stream=stream):
        progress = json.loads(line).get('progress', None)
        if progress:
            print(json.dumps(json.loads(line).get('progress'), indent=4))


def image_exists(name):
    images = [item for item in docker_client.images() if item['RepoTags']]
    image = [item for item in images if name in item.get('RepoTags', [])]
    return image != []


def remove_container_by_name(name):
    """
    Accept name filter supports wildcard.
    :param name:
    :return:
    """
    filters = {'name': name}
    containers = docker_client.containers(filters=filters, all=True)
    for container in containers:
        remove_container(container)


def remove_container_by_ip(ip):
    containers = docker_client.containers(all=True)
    for container_id in containers:
        if get_container_ip(container_id) == ip:
            return remove_container(container_id)


def remove_container(cid):
    try:
        docker_client.remove_container(cid, force=True, v=True)
        return True
    except:
        print 'failed removing container {}'.format(cid)
        return False


def get_volume(path, ro=True):
    volume = {path: {}}
    binds = {
        path: {
            'bind': path,
            'ro': ro,
        }
    }
    return volume, binds


def create_and_start_container(image,
                               command=None,
                               name=None,
                               environment=None,
                               volumes=None,
                               volume_binds=None,
                               ports=None,
                               port_bindings={}):
    container_id = docker_client.create_container(
        image=image,
        command=command,
        detach=True,
        stdin_open=True,
        volumes=volumes,
        ports=ports,
        host_config=docker_client.create_host_config(
            binds=volume_binds,
            port_bindings=port_bindings,
            network_mode='bridge',
        ),
        environment=environment,
        name=name)['Id']

    docker_client.start(container_id)
    time.sleep(1)
    return container_id


def get_container_ip(cid):
    container = docker_client.inspect_container(cid)
    return container.get('NetworkSettings').get('Networks')\
        .get('bridge').get('IPAddress')
