from photon_platform.curator import Curator

# Example usage
curator = Curator('.')
curator.create_release_branch('0.0.0', 'short description')
#  curator.merge_to_main('release-1.0.0', 'Release 1.0.0')

